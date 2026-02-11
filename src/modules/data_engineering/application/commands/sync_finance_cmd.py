import asyncio
from typing import Dict, Any, List, Optional
from loguru import logger
from src.modules.data_engineering.domain.ports.repositories.stock_basic_repo import IStockBasicRepository
from src.modules.data_engineering.domain.ports.repositories.financial_data_repo import IFinancialDataRepository
from src.modules.data_engineering.domain.ports.providers.financial_data_provider import IFinancialDataProvider
from src.modules.data_engineering.domain.model.stock import StockInfo

class SyncFinanceHistoryUseCase:
    """
    同步历史财务数据
    """
    def __init__(
        self,
        stock_repo: IStockBasicRepository,
        finance_repo: IFinancialDataRepository,
        data_provider: IFinancialDataProvider
    ):
        self.stock_repo = stock_repo
        self.finance_repo = finance_repo
        self.data_provider = data_provider

    async def execute(
        self,
        start_date: str,
        end_date: str,
        offset: int = 0,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """
        分批同步历史财务数据，避免超过 Tushare 200 次/分钟限制。
        :param offset: 跳过前 offset 只股票
        :param limit: 每批最多处理 limit 只股票
        """
        logger.info(
            f"Syncing finance history from {start_date} to {end_date}, offset={offset}, limit={limit}"
        )
        stocks = await self.stock_repo.get_all(skip=offset, limit=limit)
        total_synced = 0

        for stock in stocks:
            finances = await self.data_provider.fetch_fina_indicator(
                third_code=stock.third_code,
                start_date=start_date,
                end_date=end_date,
            )
            if finances:
                count = await self.finance_repo.save_all(finances)
                total_synced += count

        return {
            "status": "success",
            "count": total_synced,
            "batch_size": len(stocks),
        }
