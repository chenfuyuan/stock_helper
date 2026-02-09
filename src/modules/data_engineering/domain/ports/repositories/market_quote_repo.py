from abc import ABC, abstractmethod
from typing import List
from src.modules.data_engineering.domain.model.daily_bar import StockDaily

class IMarketQuoteRepository(ABC):
    @abstractmethod
    async def save_all(self, dailies: List[StockDaily]) -> int: pass
