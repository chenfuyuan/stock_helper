from abc import ABC, abstractmethod
from datetime import date
from typing import List
from src.modules.data_engineering.domain.model.daily_bar import StockDaily


class IMarketQuoteRepository(ABC):
    @abstractmethod
    async def save_all(self, dailies: List[StockDaily]) -> int:
        pass

    @abstractmethod
    async def get_by_third_code_and_date_range(
        self, third_code: str, start_date: date, end_date: date
    ) -> List[StockDaily]:
        """按第三方代码与日期区间查询日线，供 Application 层只读使用。"""
        pass
