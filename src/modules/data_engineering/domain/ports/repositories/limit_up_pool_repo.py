from abc import ABC, abstractmethod
from datetime import date

from src.modules.data_engineering.domain.model.limit_up_pool import LimitUpPoolStock


class ILimitUpPoolRepository(ABC):
    """
    涨停池数据仓储 Port
    定义涨停池数据的持久化能力
    """

    @abstractmethod
    async def save_all(self, stocks: list[LimitUpPoolStock]) -> int:
        """
        批量 UPSERT 涨停池记录（以 trade_date + third_code 为唯一键）
        
        Args:
            stocks: 涨停池股票列表
            
        Returns:
            int: 影响的行数
        """

    @abstractmethod
    async def get_by_date(self, trade_date: date) -> list[LimitUpPoolStock]:
        """
        查询指定日期的涨停池记录
        
        Args:
            trade_date: 交易日期
            
        Returns:
            list[LimitUpPoolStock]: 涨停池记录列表
        """
