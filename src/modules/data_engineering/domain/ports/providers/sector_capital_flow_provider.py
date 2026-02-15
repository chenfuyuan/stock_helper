from abc import ABC, abstractmethod

from src.modules.data_engineering.domain.dtos.capital_flow_dtos import SectorCapitalFlowDTO


class ISectorCapitalFlowProvider(ABC):
    """
    板块资金流向数据提供者 Port
    定义从外部数据源获取板块资金流向数据的能力
    """

    @abstractmethod
    async def fetch_sector_capital_flow(
        self, sector_type: str = "概念资金流"
    ) -> list[SectorCapitalFlowDTO]:
        """
        获取当日板块资金流向排名
        
        Args:
            sector_type: 板块类型（默认"概念资金流"）
            
        Returns:
            list[SectorCapitalFlowDTO]: 板块资金流向数据列表
        """
