from abc import ABC, abstractmethod
from typing import List
from app.domain.stock.entities import StockInfo, StockDaily

class StockDataProvider(ABC):
    """
    股票数据提供者接口 (Domain Service Interface)
    定义获取外部股票数据的标准契约
    """
    
    @abstractmethod
    async def fetch_stock_basic(self) -> List[StockInfo]:
        """
        获取股票基础数据列表
        """
        pass

    @abstractmethod
    async def fetch_daily(self, third_code: str = None, trade_date: str = None, start_date: str = None, end_date: str = None) -> List[StockDaily]:
        """
        获取日线行情数据
        """
        pass
