from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import date
from src.modules.market_data.domain.entities import StockInfo, StockDaily, StockFinance

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

    @abstractmethod
    async def get_missing_finance_stocks(self, target_period: str, check_threshold_date: date, limit: int = 200) -> List[str]:
        """
        获取缺少指定报告期财务数据的股票代码列表
        :param target_period: 目标报告期 (YYYYMMDD)
        :param check_threshold_date: 检查阈值日期 (在此日期之前检查过的才会被选中)
        :param limit: 限制数量
        :return: 股票代码列表 (third_code)
        """
        pass

    @abstractmethod
    async def update_last_finance_sync_date(self, third_codes: List[str], sync_date: date) -> None:
        """
        批量更新最后财务同步时间
        :param third_codes: 股票代码列表
        :param sync_date: 同步日期
        """
        pass

    @abstractmethod
    async def update_last_finance_sync_date_single(self, third_code: str, sync_date: date) -> None:
        """
        更新单个股票最后财务同步时间
        :param third_code: 股票代码
        :param sync_date: 同步日期
        """
        pass



class StockDailyRepository(ABC):
    """
    股票日线行情仓储接口
    """
    @abstractmethod
    async def save_all(self, dailies: List[StockDaily]) -> int:
        """批量保存日线数据"""
        pass

    @abstractmethod
    async def get_latest_by_third_code(self, third_code: str) -> Optional[StockDaily]:
        """获取某只股票最新的日线数据"""
        pass

class StockFinanceRepository(ABC):
    """
    股票财务指标仓储接口
    """
    @abstractmethod
    async def save_all(self, finances: List[StockFinance]) -> int:
        """批量保存财务指标数据"""
        pass
