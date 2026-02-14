from typing import Any

from loguru import logger

from src.modules.data_engineering.domain.ports.providers.stock_basic_provider import (
    IStockBasicProvider,
)
from src.modules.data_engineering.domain.ports.repositories.stock_basic_repo import (
    IStockBasicRepository,
)
from src.shared.application.use_cases import BaseUseCase

# Fix DTO import if it was moved or needs move.
# src/modules/market_data/application/dtos.py might be missing or not moved.
# I'll check if I moved dtos.py. I moved "use_cases/*".
# DTOs were in `src/modules/market_data/application/dtos.py`.
# I probably deleted it with `rm -rf`.
# I need to recreate DTOs or find where they are.
# Wait, I see "sync_stock_list_cmd.py" using SyncStockOutput.


class SyncStocksUseCase(BaseUseCase):
    """
    同步股票基础数据用例
    流程：调用 ACL 获取数据 -> 批量保存到数据库
    """

    def __init__(
        self,
        stock_repo: IStockBasicRepository,
        stock_provider: IStockBasicProvider,
    ):
        self.stock_repo = stock_repo
        self.stock_provider = stock_provider

    async def execute(self) -> Any:  # Temporary Any if DTO is missing
        logger.info("执行股票数据同步任务...")

        # 1. 从第三方服务获取清洗后的领域对象
        stocks = await self.stock_provider.fetch_stock_basic()

        if not stocks:
            logger.info("未获取到股票数据，任务结束")
            return {
                "status": "success",
                "synced_count": 0,
                "message": "No data fetched",
            }

        # 2. 持久化存储 (批量)
        saved_stocks = await self.stock_repo.save_all(stocks)

        count = len(saved_stocks)
        logger.info(f"股票数据同步完成，共更新 {count} 条记录")

        return {
            "status": "success",
            "synced_count": count,
            "message": f"Successfully synced {count} stocks",
        }
