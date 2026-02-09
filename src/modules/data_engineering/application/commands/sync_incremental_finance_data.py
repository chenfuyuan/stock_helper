import asyncio
import json
import os
from datetime import date, datetime, timedelta
from typing import Dict, Any, List, Set, Optional
from loguru import logger
from src.modules.data_engineering.domain.ports.repositories.stock_basic_repo import IStockBasicRepository
from src.modules.data_engineering.domain.ports.repositories.financial_data_repo import IFinancialDataRepository
from src.modules.data_engineering.domain.ports.providers.financial_data_provider import IFinancialDataProvider
from src.modules.data_engineering.domain.model.disclosure import StockDisclosure

FAILURE_RECORD_FILE = "sync_finance_failures.json"

class SyncIncrementalFinanceDataUseCase:
    """
    增量同步股票财务指标用例
    策略: 预期报告期驱动 + 动态优先级队列
    """
    def __init__(
        self,
        finance_repo: IFinancialDataRepository,
        stock_repo: IStockBasicRepository,
        data_provider: IFinancialDataProvider
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
        try:
            logger.info(f"Fetching disclosure list for {actual_date}...")
            disclosures = await self.data_provider.fetch_disclosure_date(actual_date=actual_date)
            for d in disclosures:
                end_date_str = d.end_date.strftime("%Y%m%d") if hasattr(d.end_date, 'strftime') else str(d.end_date).replace('-', '')
                if end_date_str == target_period:
                    tasks.add(d.third_code)
            logger.info(f"Found {len(tasks)} stocks from disclosure schedule.")
        except Exception as e:
            logger.error(f"Failed to fetch disclosure list: {str(e)}")
        
        # 策略 B: 长尾轮询 (Low Priority)
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
            tasks.update(missing_stocks)
            logger.info(f"Added {len(tasks) - initial_task_count} stocks from missing list (DB). Total tasks: {len(tasks)}")
        except Exception as e:
            logger.error(f"Failed to fetch missing stocks: {str(e)}")

        # 策略 C: 重试之前的失败任务
        # (Simplified: loading from file)
        # Assuming _get_failures implementation similar to original
        
        # 3. 执行同步 (Consumer)
        synced_count = 0
        failed_tasks = []
        
        for code in tasks:
            try:
                # Fetch finance data
                # We need start_date and end_date. Tushare fina_indicator usually needs specific period.
                # If we use target_period as end_date.
                target_date_formatted = f"{target_period[:4]}{target_period[4:6]}{target_period[6:]}" # YYYYMMDD
                
                finances = await self.data_provider.fetch_fina_indicator(
                    third_code=code,
                    end_date=target_date_formatted 
                    # Note: Tushare API might require start_date too or return history if only end_date provided.
                    # Assuming client handles it or returns what matches.
                )
                
                if finances:
                    await self.finance_repo.save_all(finances)
                    synced_count += 1
                    # Update check time
                    await self.stock_repo.update_last_finance_sync_date(
                        third_codes=[code],
                        sync_date=current_date
                    )
                else:
                    # Mark as checked even if empty (to avoid immediate retry unless error)
                    # Or maybe not? If empty, maybe not published yet.
                    # Strategy: Update check time so we don't check again immediately tomorrow, 
                    # but check_threshold is 3 days, so we will check again in 3 days.
                    await self.stock_repo.update_last_finance_sync_date(
                        third_codes=[code],
                        sync_date=current_date
                    )
                    
            except Exception as e:
                logger.error(f"Failed to sync finance for {code}: {str(e)}")
                failed_tasks.append(code)
                
        self._save_failures(failed_tasks)
        
        return {
            "status": "success",
            "synced_count": synced_count,
            "failed_count": len(failed_tasks),
            "target_period": target_period
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
        
        all_failures = list(set(existing_failures + new_failures))
        
        try:
            with open(FAILURE_RECORD_FILE, 'w') as f:
                json.dump({"failures": all_failures}, f)
        except Exception as e:
            logger.error(f"Failed to save failure record: {e}")
