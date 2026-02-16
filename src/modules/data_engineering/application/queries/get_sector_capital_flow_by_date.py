from datetime import date

from src.modules.data_engineering.application.dtos.market_data_query_dtos import (
    SectorCapitalFlowDTO,
)
from src.modules.data_engineering.domain.ports.repositories.sector_capital_flow_repo import (
    ISectorCapitalFlowRepository,
)


class GetSectorCapitalFlowByDateUseCase:
    """
    按日期查询板块资金流向数据用例。

    返回 DTO 而非 Domain Entity，确保跨模块接口不暴露内部实体。
    """

    def __init__(self, sector_capital_flow_repo: ISectorCapitalFlowRepository):
        self.sector_capital_flow_repo = sector_capital_flow_repo

    async def execute(
        self, trade_date: date, sector_type: str | None = None
    ) -> list[SectorCapitalFlowDTO]:
        """
        查询指定日期的板块资金流向记录。

        Args:
            trade_date: 交易日期
            sector_type: 板块类型（可选，用于过滤）

        Returns:
            板块资金流向 DTO 列表
        """
        entities = await self.sector_capital_flow_repo.get_by_date(trade_date, sector_type)
        return [
            SectorCapitalFlowDTO(
                trade_date=e.trade_date,
                sector_name=e.sector_name,
                sector_type=e.sector_type,
                net_amount=e.net_amount,
                inflow_amount=e.inflow_amount,
                outflow_amount=e.outflow_amount,
                pct_chg=e.pct_chg,
            )
            for e in entities
        ]
