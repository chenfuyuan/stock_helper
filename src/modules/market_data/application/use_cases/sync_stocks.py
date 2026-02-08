from typing import List, Dict, Any
from loguru import logger
from src.shared.application.use_cases import BaseUseCase
from src.modules.market_data.domain.repositories import StockRepository
from src.modules.market_data.domain.services import StockDataProvider
from src.modules.market_data.application.dtos import SyncStockOutput

class SyncStocksUseCase(BaseUseCase):
    """
    同步股票基础数据用例
    流程：调用 ACL 获取数据 -> 批量保存到数据库
    """
    def __init__(self, stock_repo: StockRepository, stock_provider: StockDataProvider):
        self.stock_repo = stock_repo
        self.stock_provider = stock_provider

    async def execute(self) -> SyncStockOutput:
        logger.info("执行股票数据同步任务...")
        
        # 1. 从第三方服务获取清洗后的领域对象
        stocks = await self.stock_provider.fetch_stock_basic()
        
        if not stocks:
            logger.info("未获取到股票数据，任务结束")
            return SyncStockOutput(
                status="success", 
                synced_count=0, 
                message="No data fetched"
            )
            
        # 2. 持久化存储 (批量)
        # 考虑到数据量可能较大 (5000+)，在生产环境中可能需要分批处理
        # 这里演示简单的一次性保存
        saved_stocks = await self.stock_repo.save_all(stocks)
        
        count = len(saved_stocks)
        logger.info(f"股票数据同步完成，共更新 {count} 条记录")
        
        return SyncStockOutput(
            status="success",
            synced_count=count,
            message=f"Successfully synced {count} stocks"
        )
