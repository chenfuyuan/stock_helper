from datetime import date

from src.modules.data_engineering.domain.model.sector_capital_flow import SectorCapitalFlow
from src.modules.data_engineering.domain.ports.repositories.sector_capital_flow_repo import (
    ISectorCapitalFlowRepository,
)
from src.shared.application.use_cases import BaseUseCase


class GetSectorCapitalFlowByDateUseCase(BaseUseCase):
    """
    按日期查询板块资金流向数据用例
    """

    def __init__(self, sector_capital_flow_repo: ISectorCapitalFlowRepository):
        self.sector_capital_flow_repo = sector_capital_flow_repo

    async def execute(
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
        return await self.sector_capital_flow_repo.get_by_date(trade_date, sector_type)
