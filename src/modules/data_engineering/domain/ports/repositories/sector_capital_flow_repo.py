from abc import ABC, abstractmethod
from datetime import date

from src.modules.data_engineering.domain.model.sector_capital_flow import SectorCapitalFlow


class ISectorCapitalFlowRepository(ABC):
    """
    板块资金流向数据仓储 Port
    定义板块资金流向数据的持久化能力
    """

    @abstractmethod
    async def save_all(self, flows: list[SectorCapitalFlow]) -> int:
        """
        批量 UPSERT 板块资金流向记录（以 trade_date + sector_name + sector_type 为唯一键）
        
        Args:
            flows: 板块资金流向列表
            
        Returns:
            int: 影响的行数
        """

    @abstractmethod
    async def get_by_date(
        self, trade_date: date, sector_type: str | None = None
    ) -> list[SectorCapitalFlow]:
        """
        查询指定日期的板块资金流向记录
        
        Args:
            trade_date: 交易日期
            sector_type: 板块类型（可选，用于过滤）
            
        Returns:
            list[SectorCapitalFlow]: 板块资金流向记录列表
        """
