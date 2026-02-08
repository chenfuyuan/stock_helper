import asyncio
import json
import os
from datetime import date, datetime, timedelta
from typing import Dict, Any, List, Set, Optional
from loguru import logger
from app.domain.stock.repository import StockRepository, StockFinanceRepository
from app.domain.stock.service import StockDataProvider
from app.domain.stock.entities import StockDisclosure

FAILURE_RECORD_FILE = "sync_finance_failures.json"

class SyncIncrementalFinanceDataUseCase:
    """
    增量同步股票财务指标用例
    策略: 预期报告期驱动 + 动态优先级队列
    """
    def __init__(
        self,
        finance_repo: StockFinanceRepository,
        stock_repo: StockRepository,
        data_provider: StockDataProvider
    ):
        self.finance_repo = finance_repo
        self.stock_repo = stock_repo
        self.data_provider = data_provider

    def _get_target_period(self, current_date: date) -> str:
        """根据当前日期确定目标报告期"""
        year = current_date.year
        month = current_date.month
        
        if 1 <= month <= 4:
            # 1-4月，目标是去年的年报 (Q4)
            return f"{year-1}1231"
        elif 5 <= month <= 8:
            # 5-8月，目标是今年的一季报 (Q1)
            return f"{year}0331"
        elif 9 <= month <= 10:
            # 9-10月，目标是今年的中报 (Q2)
            return f"{year}0630"
        else:
            # 11-12月，目标是今年的三季报 (Q3)
            return f"{year}0930"

    async def execute(self, actual_date: str = None) -> Dict[str, Any]:
        """
        执行增量同步逻辑
        :param actual_date: 可选，用于模拟日期 (YYYYMMDD)
        :return: 同步结果
        """
        # 1. 确定基准日期和目标报告期
        if actual_date:
            try:
                current_date = datetime.strptime(actual_date, "%Y%m%d").date()
            except ValueError:
                current_date = date.today()
        else:
            current_date = date.today()
            actual_date = current_date.strftime("%Y%m%d")
            
        target_period = self._get_target_period(current_date)
        logger.info(f"Starting incremental finance sync. Current Date: {actual_date}, Target Period: {target_period}")

        # 2. 构建任务队列
        tasks: Set[str] = set()
        
        # 策略 A: 获取今日披露名单 (High Priority)
        # 虽然 disclosure_date 不完全可靠，但它是一个很好的 "即时信号"
        try:
            logger.info(f"Fetching disclosure list for {actual_date}...")
            disclosures = await self.data_provider.fetch_disclosure_date(actual_date=actual_date)
            # 过滤出针对目标报告期（或更晚，防止补发）的披露
            # 简单起见，只要是今天披露的，我们都纳入检查范围，因为 fetch_disclosure_date 返回的是 Disclosure 对象
            # 我们主要关心那些 end_date == target_period 的，或者简单的把所有今天披露的股票都加入待查队列
            for d in disclosures:
                # 我们可以稍微放宽一点，不只查 target_period，因为可能补发以前的
                # 但为了聚焦，我们主要关注 target_period
                end_date_str = d.end_date.strftime("%Y%m%d") if hasattr(d.end_date, 'strftime') else str(d.end_date).replace('-', '')
                if end_date_str == target_period:
                    tasks.add(d.third_code)
            logger.info(f"Found {len(tasks)} stocks from disclosure schedule.")
        except Exception as e:
            logger.error(f"Failed to fetch disclosure list: {str(e)}")
            # 不阻断，继续执行策略 B
        
        # 策略 B: 长尾轮询 (Low Priority)
        # 从数据库中找出：缺少目标报告期数据 且 (从未检查过 OR 3天前检查过) 的股票
        # 限制数量，防止每天跑太多
        check_threshold = current_date - timedelta(days=3)
        limit = 300  # 每日补充轮询上限
        
        try:
            logger.info(f"Fetching missing stocks from DB (Limit: {limit})...")
            missing_stocks = await self.stock_repo.get_missing_finance_stocks(
                target_period=target_period,
                check_threshold_date=check_threshold,
                limit=limit
            )
            initial_task_count = len(tasks)
            for code in missing_stocks:
                tasks.add(code)
            logger.info(f"Added {len(tasks) - initial_task_count} stocks from missing pool.")
        except Exception as e:
            logger.error(f"Failed to fetch missing stocks from DB: {str(e)}")

        if not tasks:
            logger.info("No tasks to process.")
            return {"status": "success", "message": "No tasks", "synced_count": 0}

        # 3. 执行同步
        logger.info(f"Total unique stocks to sync: {len(tasks)}")
        
        synced_count = 0
        total_rows = 0
        failed_tasks = []
        processed_codes = []
        
        # 将 set 转为 list 并排序，保证顺序一致性
        sorted_tasks = sorted(list(tasks))
        
        for i, code in enumerate(sorted_tasks):
            try:
                # 调用 Tushare 接口获取数据
                # 注意：我们明确查询 target_period
                finances = await self.data_provider.fetch_fina_indicator(
                    third_code=code,
                    start_date=target_period,
                    end_date=target_period
                )
                
                if finances:
                    # 有数据 -> 保存
                    saved = await self.finance_repo.save_all(finances)
                    logger.info(f"[{i+1}/{len(tasks)}] Synced {code} for {target_period}: {saved} rows.")
                    if saved > 0:
                        synced_count += 1
                        total_rows += saved
                else:
                    # 无数据 -> 仅记录日志，后续会更新 check_time
                    logger.debug(f"[{i+1}/{len(tasks)}] No data for {code} in period {target_period}")

                # 独立事务：立即更新该股票的同步时间
                # 这样即使后续任务失败，当前成功的任务状态也会被保存
                await self.stock_repo.update_last_finance_sync_date_single(code, current_date)

            except Exception as e:
                logger.error(f"Failed to sync {code}: {str(e)}")
                # 记录失败，用于重试 (格式: code|period)
                failed_tasks.append(f"{code}|{target_period}")
            
            # 严格串行执行，遵守 Tushare 限制 (每分钟 200 次 -> 0.3s/次, 安全起见 0.4s)
            await asyncio.sleep(0.4)


        # 5. 记录失败任务到文件 (用于后续补偿)
        if failed_tasks:
            self._save_failures(failed_tasks)
            
        return {
            "status": "success",
            "message": f"Synced {synced_count} stocks, {total_rows} rows. {len(failed_tasks)} failed.",
            "synced_count": synced_count,
            "total_rows": total_rows,
            "failed_count": len(failed_tasks)
        }

    def _save_failures(self, new_failures: List[str]):
        """保存失败任务到文件 (追加模式)"""
        existing_failures = []
        if os.path.exists(FAILURE_RECORD_FILE):
            try:
                with open(FAILURE_RECORD_FILE, 'r') as f:
                    data = json.load(f)
                    existing_failures = data.get("failures", [])
            except Exception:
                pass
        
        # 合并并去重
        all_failures = list(set(existing_failures + new_failures))
        
        try:
            with open(FAILURE_RECORD_FILE, 'w') as f:
                json.dump({"failures": all_failures}, f)
        except Exception as e:
            logger.error(f"Failed to save failure record: {e}")
