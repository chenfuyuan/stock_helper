from abc import ABC, abstractmethod
from datetime import date

from src.modules.data_engineering.domain.model.previous_limit_up import PreviousLimitUpStock


class IPreviousLimitUpRepository(ABC):
    """
    昨日涨停表现数据仓储 Port
    定义昨日涨停表现数据的持久化能力
    """

    @abstractmethod
    async def save_all(self, stocks: list[PreviousLimitUpStock]) -> int:
        """
        批量 UPSERT 昨日涨停表现记录（以 trade_date + third_code 为唯一键）
        
        Args:
            stocks: 昨日涨停表现股票列表
            
        Returns:
            int: 影响的行数
        """

    @abstractmethod
    async def get_by_date(self, trade_date: date) -> list[PreviousLimitUpStock]:
        """
        查询指定日期的昨日涨停表现记录
        
        Args:
            trade_date: 交易日期
            
        Returns:
            list[PreviousLimitUpStock]: 昨日涨停表现记录列表
        """
