from abc import ABC, abstractmethod
from datetime import date
from typing import List, Optional

from src.modules.data_engineering.domain.model.stock import StockInfo


class IStockBasicRepository(ABC):
    @abstractmethod
    async def save(self, stock: StockInfo) -> StockInfo:
        pass

    @abstractmethod
    async def save_all(self, stocks: List[StockInfo]) -> List[StockInfo]:
        pass

    @abstractmethod
    async def get_by_symbol(self, symbol: str) -> Optional[StockInfo]:
        pass

    @abstractmethod
    async def get_by_third_code(self, third_code: str) -> Optional[StockInfo]:
        pass

    @abstractmethod
    async def get_by_third_codes(
        self, third_codes: List[str]
    ) -> List[StockInfo]:
        pass

    @abstractmethod
    async def get_all(
        self, skip: int = 0, limit: int = 100
    ) -> List[StockInfo]:
        pass

    @abstractmethod
    async def get_missing_finance_stocks(
        self, target_period: str, check_threshold_date: date, limit: int = 200
    ) -> List[str]:
        pass

    @abstractmethod
    async def update_last_finance_sync_date(
        self, third_codes: List[str], sync_date: date
    ) -> None:
        pass
