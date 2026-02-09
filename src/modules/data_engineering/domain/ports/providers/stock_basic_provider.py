from abc import ABC, abstractmethod
from typing import List
from src.modules.data_engineering.domain.model.stock import StockInfo

class IStockBasicProvider(ABC):
    @abstractmethod
    async def fetch_stock_basic(self) -> List[StockInfo]:
        """Fetch basic stock information."""
        pass
