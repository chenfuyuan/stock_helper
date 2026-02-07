from abc import ABC, abstractmethod
from typing import List
from app.domain.stock.entity import StockInfo

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
