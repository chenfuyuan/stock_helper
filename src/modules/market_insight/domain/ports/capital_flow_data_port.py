from abc import ABC, abstractmethod
from datetime import date

from src.modules.market_insight.domain.dtos.capital_flow_dtos import (
    DragonTigerItemDTO,
    SectorCapitalFlowItemDTO,
)


class ICapitalFlowDataPort(ABC):
    """
    资金流向数据端口（MI 领域层接口）
    用于从 data_engineering 模块消费资金行为相关数据
    """

    @abstractmethod
    async def get_dragon_tiger(self, trade_date: date) -> list[DragonTigerItemDTO]:
        """
        获取指定日期的龙虎榜详情
        
        Args:
            trade_date: 交易日期
            
        Returns:
            list[DragonTigerItemDTO]: 龙虎榜数据列表
        """
        pass

    @abstractmethod
    async def get_sector_capital_flow(
        self, trade_date: date, sector_type: str | None = None
    ) -> list[SectorCapitalFlowItemDTO]:
        """
        获取指定日期的板块资金流向
        
        Args:
            trade_date: 交易日期
            sector_type: 板块类型（可选，用于过滤）
            
        Returns:
            list[SectorCapitalFlowItemDTO]: 板块资金流向数据列表
        """
        pass
