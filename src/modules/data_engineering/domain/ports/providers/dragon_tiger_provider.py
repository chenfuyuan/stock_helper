from abc import ABC, abstractmethod
from datetime import date

from src.modules.data_engineering.domain.dtos.dragon_tiger_dtos import DragonTigerDetailDTO


class IDragonTigerProvider(ABC):
    """
    龙虎榜数据提供者 Port
    定义从外部数据源获取龙虎榜详情数据的能力
    """

    @abstractmethod
    async def fetch_dragon_tiger_detail(self, trade_date: date) -> list[DragonTigerDetailDTO]:
        """
        获取指定日期的龙虎榜详情数据
        
        Args:
            trade_date: 交易日期
            
        Returns:
            list[DragonTigerDetailDTO]: 龙虎榜详情数据列表
        """
