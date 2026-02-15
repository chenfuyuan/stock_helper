from abc import ABC, abstractmethod
from datetime import date

from src.modules.data_engineering.domain.model.dragon_tiger import DragonTigerDetail


class IDragonTigerRepository(ABC):
    """
    龙虎榜数据仓储 Port
    定义龙虎榜数据的持久化能力
    """

    @abstractmethod
    async def save_all(self, details: list[DragonTigerDetail]) -> int:
        """
        批量 UPSERT 龙虎榜记录（以 trade_date + third_code + reason 为唯一键）
        
        Args:
            details: 龙虎榜详情列表
            
        Returns:
            int: 影响的行数
        """

    @abstractmethod
    async def get_by_date(self, trade_date: date) -> list[DragonTigerDetail]:
        """
        查询指定日期的龙虎榜记录
        
        Args:
            trade_date: 交易日期
            
        Returns:
            list[DragonTigerDetail]: 龙虎榜记录列表
        """
