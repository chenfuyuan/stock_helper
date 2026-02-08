import asyncio
from datetime import date
from typing import Dict, Any, List
from loguru import logger
from app.domain.stock.repository import StockRepository, StockFinanceRepository
from app.domain.stock.service import StockDataProvider
from app.domain.stock.entities import StockDisclosure

class SyncIncrementalFinanceDataUseCase:
    """
    增量同步股票财务指标用例
    基于 Tushare disclosure_date 接口
    """
    def __init__(
        self,
        finance_repo: StockFinanceRepository,
        data_provider: StockDataProvider
    ):
        self.finance_repo = finance_repo
        self.data_provider = data_provider

    async def execute(self, actual_date: str = None) -> Dict[str, Any]:
        """
        执行增量同步逻辑
        :param actual_date: 实际披露日期，默认为当天
        :return: 同步结果
        """
        # 1. 获取今日披露名单
        if not actual_date:
            actual_date = date.today().strftime("%Y%m%d")
            
        logger.info(f"Checking for stock finance updates for date: {actual_date}...")
        
        try:
            disclosures = await self.data_provider.fetch_disclosure_date(actual_date=actual_date)
        except Exception as e:
            logger.error(f"Failed to fetch disclosure list: {str(e)}")
            return {
                "status": "failed", 
                "message": str(e),
                "synced_count": 0
            }
            
        if not disclosures:
            logger.info("No disclosures found for today.")
            return {
                "status": "success",
                "message": "No disclosures found",
                "synced_count": 0,
                "total_rows": 0
            }

        # 2. 去重与任务生成 (ts_code, end_date)
        # 尽管通常一家公司一天只披露一次，但为了保险起见进行去重
        tasks = []
        seen = set()
        
        for d in disclosures:
            key = (d.third_code, d.end_date)
            if key not in seen:
                seen.add(key)
                tasks.append(d)
                
        logger.info(f"Found {len(tasks)} unique finance reports to sync.")
        
        synced_count = 0
        total_rows = 0
        failed_tasks = []
        
        # 3. 逐个同步（量通常不大，串行或小并发即可）
        # 这里使用 Semaphore 稍微控制一下并发
        semaphore = asyncio.Semaphore(5)
        
        async def sync_task(disclosure: StockDisclosure):
            nonlocal synced_count, total_rows
            async with semaphore:
                try:
                    # 获取该股票特定报告期的数据
                    # end_date 格式可能是 date 对象，需要转为 string
                    end_date_str = disclosure.end_date.strftime("%Y%m%d") if hasattr(disclosure.end_date, 'strftime') else str(disclosure.end_date).replace('-', '')
                    
                    # 这里的 start_date 和 end_date 都设为报告期，精准获取那一期的数据
                    finances = await self.data_provider.fetch_fina_indicator(
                        third_code=disclosure.third_code,
                        start_date=end_date_str,
                        end_date=end_date_str
                    )
                    
                    if finances:
                        saved = await self.finance_repo.save_all(finances)
                        logger.info(f"Synced {disclosure.third_code} for period {end_date_str}: {saved} rows.")
                        if saved > 0:
                            synced_count += 1
                            total_rows += saved
                    else:
                        logger.warning(f"No finance data returned for {disclosure.third_code} period {end_date_str}")
                        
                    # 简单限流
                    await asyncio.sleep(0.2)
                        
                except Exception as e:
                    logger.error(f"Failed to sync {disclosure.third_code}: {str(e)}")
                    failed_tasks.append(f"{disclosure.third_code}|{disclosure.end_date}")

        # 并发执行
        await asyncio.gather(*[sync_task(t) for t in tasks])
        
        return {
            "status": "success",
            "synced_stocks_count": synced_count,
            "total_rows_updated": total_rows,
            "failed_tasks": failed_tasks,
            "total_tasks": len(tasks)
        }
