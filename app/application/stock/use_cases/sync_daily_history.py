import asyncio
from typing import Dict, Any
from loguru import logger
from app.domain.stock.repository import StockRepository, StockDailyRepository
from app.domain.stock.service import StockDataProvider

class SyncDailyHistoryUseCase:
    """
    同步股票日线历史数据用例
    """
    def __init__(
        self,
        stock_repo: StockRepository,
        daily_repo: StockDailyRepository,
        data_provider: StockDataProvider
    ):
        self.stock_repo = stock_repo
        self.daily_repo = daily_repo
        self.data_provider = data_provider

    async def execute(self, limit: int = 10, offset: int = 0) -> Dict[str, Any]:
        """
        执行同步逻辑（支持分页）
        采用生产者-消费者模型：
        - 生产者：并发获取 Tushare 数据，放入队列
        - 消费者：串行从队列取出数据，存入数据库（保证 Session 安全和事务独立）
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

        logger.info(f"Starting sync for {len(target_stocks)} stocks (offset={offset})...")
        
        synced_stocks_count = 0
        total_rows_saved = 0
        
        # 限制并发数为 5，避免触发 Tushare 限流
        semaphore = asyncio.Semaphore(5)
        # 限制队列大小，防止生产速度过快导致内存暴涨
        queue = asyncio.Queue(maxsize=5)
        
        # --- 生产者：获取数据 ---
        async def producer(stock):
            async with semaphore:
                try:
                    if not stock.third_code:
                        return
                        
                    logger.info(f"Fetching daily data for {stock.third_code} ({stock.name})...")
                    dailies = await self.data_provider.fetch_daily(third_code=stock.third_code)
                    
                    if dailies:
                        logger.info(f"Fetched {len(dailies)} records for {stock.third_code}. Putting into queue...")
                        # 将数据放入队列，如果队列满了会等待
                        await queue.put((stock, dailies))
                    else:
                        logger.warning(f"No daily data found for {stock.third_code}")
                    
                    # 避免请求过于频繁
                    await asyncio.sleep(0.1)
                        
                except Exception as e:
                    logger.error(f"Failed to fetch daily data for {stock.third_code}: {str(e)}")

        # --- 消费者：入库数据 ---
        async def consumer():
            nonlocal synced_stocks_count, total_rows_saved
            while True:
                # 从队列获取数据
                item = await queue.get()
                
                # 结束信号
                if item is None:
                    queue.task_done()
                    break
                
                stock, dailies = item
                try:
                    logger.info(f"Saving {len(dailies)} records for {stock.third_code} into DB...")
                    # 串行入库，每次 save_all 是独立事务
                    saved_count = await self.daily_repo.save_all(dailies)
                    total_rows_saved += saved_count
                    synced_stocks_count += 1
                    logger.info(f"Successfully saved {saved_count} records for {stock.third_code}")
                except Exception as e:
                    logger.error(f"Failed to save data for {stock.third_code} to DB: {str(e)}")
                finally:
                    # 标记任务完成
                    queue.task_done()

        # 启动消费者任务
        consumer_task = asyncio.create_task(consumer())
        
        # 启动生产者任务
        producer_tasks = [producer(stock) for stock in target_stocks]
        
        # 等待所有生产者完成
        await asyncio.gather(*producer_tasks)
        
        # 发送结束信号给消费者
        await queue.put(None)
        
        # 等待消费者完成
        await consumer_task
        
        return {
            "synced_stocks": synced_stocks_count,
            "total_rows": total_rows_saved,
            "message": f"Processed {len(target_stocks)} stocks, successfully synced {synced_stocks_count} stocks."
        }
