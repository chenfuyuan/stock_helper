from abc import ABC, abstractmethod
from typing import List, Optional
from src.modules.data_engineering.domain.model.stock_daily import StockDaily

class IMarketQuoteProvider(ABC):
    @abstractmethod
    async def fetch_daily(self, third_code: Optional[str] = None, trade_date: Optional[str] = None, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[StockDaily]:
        """Fetch daily market quotes."""
        pass
