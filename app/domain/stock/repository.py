from abc import ABC, abstractmethod
from typing import List, Optional
from app.domain.stock.entity import StockInfo

class StockRepository(ABC):
    """
    股票仓储接口
    Stock Repository Interface
    """
    
    @abstractmethod
    async def save(self, stock: StockInfo) -> StockInfo:
        """保存单个股票信息"""
        pass

    @abstractmethod
    async def save_all(self, stocks: List[StockInfo]) -> List[StockInfo]:
        """批量保存股票信息"""
        pass
    
    @abstractmethod
    async def get_by_symbol(self, symbol: str) -> Optional[StockInfo]:
        """根据股票代码查询"""
        pass
        
    @abstractmethod
    async def get_by_third_code(self, third_code: str) -> Optional[StockInfo]:
        """根据第三方代码查询"""
        pass
