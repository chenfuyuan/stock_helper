from abc import ABC, abstractmethod
from typing import List, Optional
from app.domain.stock.entities import StockInfo, StockDaily

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

    @abstractmethod
    async def get_all(self, skip: int = 0, limit: int = 100) -> List[StockInfo]:
        """获取所有股票（支持分页）"""
        pass

class StockDailyRepository(ABC):
    """
    股票日线行情仓储接口
    """
    @abstractmethod
    async def save_all(self, dailies: List[StockDaily]) -> int:
        """批量保存日线数据"""
        pass
