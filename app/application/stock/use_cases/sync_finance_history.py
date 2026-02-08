import asyncio
from typing import Dict, Any
from loguru import logger
from app.domain.stock.repository import StockRepository, StockFinanceRepository
from app.domain.stock.service import StockDataProvider

class SyncFinanceHistoryUseCase:
    """
    同步股票财务指标历史数据用例
    """
    def __init__(
        self,
        stock_repo: StockRepository,
        finance_repo: StockFinanceRepository,
        data_provider: StockDataProvider
    ):
        self.stock_repo = stock_repo
        self.finance_repo = finance_repo
        self.data_provider = data_provider

    async def execute(self, limit: int = 10, offset: int = 0) -> Dict[str, Any]:
        """
        执行同步逻辑（支持分页）
        采用生产者-消费者模型
        """
        # 1. 获取目标股票列表
        target_stocks = await self.stock_repo.get_all(skip=offset, limit=limit)
        
        if not target_stocks:
            logger.warning(f"No stocks found to sync (offset={offset}, limit={limit})")
            return {
                "synced_stocks": 0,
                "total_rows": 0,
                "message": f"No stocks found to sync (offset={offset}, limit={limit})"
            }

        logger.info(f"Starting finance sync for {len(target_stocks)} stocks (offset={offset})...")
        
        synced_stocks_count = 0
        total_rows_saved = 0
        
        # 限制并发数为 5，避免触发 Tushare 限流
        semaphore = asyncio.Semaphore(5)
        # 限制队列大小
        queue = asyncio.Queue(maxsize=5)
        
        # --- 生产者：获取数据 ---
        async def producer(stock):
            async with semaphore:
                try:
                    if not stock.third_code:
                        return
                        
                    logger.info(f"Fetching finance data for {stock.third_code} ({stock.name})...")
                    finances = await self.data_provider.fetch_fina_indicator(third_code=stock.third_code)
                    
                    if finances:
                        logger.info(f"Fetched {len(finances)} finance records for {stock.third_code}. Putting into queue...")
                        await queue.put((stock, finances))
                    else:
                        logger.warning(f"No finance data found for {stock.third_code}")
                    
                    await asyncio.sleep(0.1)
                        
                except Exception as e:
                    logger.error(f"Failed to fetch finance data for {stock.third_code}: {str(e)}")

        # --- 消费者：入库数据 ---
        async def consumer():
            nonlocal synced_stocks_count, total_rows_saved
            while True:
                item = await queue.get()
                
                if item is None:
                    queue.task_done()
                    break
                
                stock, finances = item
                try:
                    logger.info(f"Saving {len(finances)} finance records for {stock.third_code} into DB...")
                    saved_count = await self.finance_repo.save_all(finances)
                    total_rows_saved += saved_count
                    synced_stocks_count += 1
                    logger.info(f"Successfully saved {saved_count} finance records for {stock.third_code}")
                except Exception as e:
                    logger.error(f"Failed to save finance data for {stock.third_code} to DB: {str(e)}")
                    await self.finance_repo.session.rollback()
                finally:
                    queue.task_done()

        # 启动消费者任务
        consumer_task = asyncio.create_task(consumer())
        
        # 启动生产者任务
        producers = [producer(stock) for stock in target_stocks]
        await asyncio.gather(*producers)
        
        # 生产者完成后，发送结束信号
        await queue.put(None)
        
        # 等待消费者完成
        await consumer_task
        
        logger.info(f"Sync finance batch completed. Synced {synced_stocks_count} stocks, {total_rows_saved} rows.")
        
        return {
            "synced_stocks": synced_stocks_count,
            "total_rows": total_rows_saved,
            "message": f"Synced {synced_stocks_count} stocks ({total_rows_saved} rows) in this batch (offset={offset})"
        }
