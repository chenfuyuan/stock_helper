from abc import ABC, abstractmethod
from typing import List
from src.modules.data_engineering.domain.model.financial_report import StockFinance

class IFinancialDataRepository(ABC):
    @abstractmethod
    async def save_all(self, finances: List[StockFinance]) -> int: pass
