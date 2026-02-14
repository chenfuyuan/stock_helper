from abc import ABC, abstractmethod
from typing import List

from src.modules.data_engineering.domain.model.financial_report import (
    StockFinance,
)


class IFinancialDataRepository(ABC):
    @abstractmethod
    async def save_all(self, finances: List[StockFinance]) -> int:
        pass

    @abstractmethod
    async def get_by_third_code_recent(
        self, third_code: str, limit: int
    ) -> List[StockFinance]:
        """按第三方代码查询最近 N 期财务记录，按 end_date 降序返回。"""
