from abc import ABC, abstractmethod
from typing import List, Optional
from src.modules.data_engineering.domain.model.financial_report import StockFinance
from src.modules.data_engineering.domain.model.disclosure import StockDisclosure

class IFinancialDataProvider(ABC):
    @abstractmethod
    async def fetch_disclosure_date(self, actual_date: Optional[str] = None) -> List[StockDisclosure]:
        """Fetch financial report disclosure dates."""
        pass

    @abstractmethod
    async def fetch_fina_indicator(self, third_code: Optional[str] = None, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[StockFinance]:
        """Fetch financial indicators."""
        pass
