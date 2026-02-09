import asyncio
from typing import Dict, Any
from loguru import logger
from src.modules.data_engineering.domain.ports.repositories.stock_basic_repo import IStockBasicRepository
from src.modules.data_engineering.domain.ports.repositories.market_quote_repo import IMarketQuoteRepository
from src.modules.data_engineering.domain.ports.providers.market_quote_provider import IMarketQuoteProvider

class SyncDailyHistoryUseCase:
    """
    同步股票日线历史数据用例
    """
    def __init__(
        self,
        stock_repo: IStockBasicRepository,
        daily_repo: IMarketQuoteRepository,
        data_provider: IMarketQuoteProvider
    ):
        self.stock_repo = stock_repo
        self.daily_repo = daily_repo
        self.data_provider = data_provider

    async def execute(self, limit: int = 10, offset: int = 0) -> Dict[str, Any]:
        """
        执行同步逻辑（支持分页）
        """
        target_stocks = await self.stock_repo.get_all(skip=offset, limit=limit)
        
        if not target_stocks:
            logger.warning(f"No stocks found to sync (offset={offset}, limit={limit})")
            return {
                "synced_stocks": 0,
                "total_rows": 0,
                "message": f"No stocks found to sync (offset={offset}, limit={limit})"
            }

        logger.info(f"Starting sync for {len(target_stocks)} stocks (offset={offset})...")
        
        synced_stocks_count = 0
        total_rows_saved = 0
        
        semaphore = asyncio.Semaphore(5)
        queue = asyncio.Queue(maxsize=5)
        
        async def producer(stock):
            async with semaphore:
                try:
                    if not stock.third_code:
                        return
                        
                    logger.info(f"Fetching daily data for {stock.third_code} ({stock.name})...")
                    dailies = await self.data_provider.fetch_daily(third_code=stock.third_code)
                    
                    if dailies:
                        logger.info(f"Fetched {len(dailies)} records for {stock.third_code}. Putting into queue...")
                        await queue.put((stock, dailies))
                    else:
                        logger.warning(f"No daily data found for {stock.third_code}")
                    
                    await asyncio.sleep(0.1)
                        
                except Exception as e:
                    logger.error(f"Failed to fetch daily data for {stock.third_code}: {str(e)}")

        async def consumer():
            nonlocal synced_stocks_count, total_rows_saved
            while True:
                item = await queue.get()
                
                if item is None:
                    queue.task_done()
                    break
                
                stock, dailies = item
                try:
                    logger.info(f"Saving {len(dailies)} records for {stock.third_code} into DB...")
                    saved_count = await self.daily_repo.save_all(dailies)
                    total_rows_saved += saved_count
                    synced_stocks_count += 1
                    logger.info(f"Successfully saved {saved_count} records for {stock.third_code}")
                except Exception as e:
                    logger.error(f"Failed to save data for {stock.third_code} to DB: {str(e)}")
                    # Assuming repo has access to session or handles rollback internally
                    # BaseRepository usually doesn't expose session directly in interface, 
                    # but Implementation has it. Interface doesn't have rollback.
                    # We might need to handle exception gracefully.
                finally:
                    queue.task_done()

        consumer_task = asyncio.create_task(consumer())
        
        producers = [producer(stock) for stock in target_stocks]
        await asyncio.gather(*producers)
        
        await queue.put(None)
        await consumer_task
        
        return {
            "synced_stocks": synced_stocks_count,
            "total_rows": total_rows_saved,
            "message": f"Synced {synced_stocks_count} stocks, total {total_rows_saved} rows"
        }
