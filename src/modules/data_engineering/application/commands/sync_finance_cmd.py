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

    async def execute(self, start_date: str, end_date: str) -> Dict[str, Any]:
        logger.info(f"Syncing finance history from {start_date} to {end_date}")
        
        # Simple implementation for demonstration
        # In reality, this might iterate over stocks or dates
        
        # Fetch stocks first? Or just fetch by date range if provider supports it?
        # Tushare finance indicator supports date range but usually requires ts_code if range is too large.
        # Assuming we fetch for all stocks (pagination needed in real world).
        
        # Strategy: Fetch all stocks, then loop (slow) or use bulk fetching if possible.
        # Tushare API limits might apply.
        
        stocks = await self.stock_repo.get_all(limit=5000)
        total_synced = 0
        
        for stock in stocks:
             finances = await self.data_provider.fetch_fina_indicator(
                 third_code=stock.third_code, 
                 start_date=start_date, 
                 end_date=end_date
             )
             if finances:
                 count = await self.finance_repo.save_all(finances)
                 total_synced += count
                 
        return {
            "status": "success",
            "count": total_synced
        }
