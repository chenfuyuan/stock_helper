from datetime import date

from src.modules.data_engineering.application.queries.get_dragon_tiger_by_date import (
    GetDragonTigerByDateUseCase,
)
from src.modules.data_engineering.application.queries.get_sector_capital_flow_by_date import (
    GetSectorCapitalFlowByDateUseCase,
)
from src.modules.market_insight.domain.dtos.capital_flow_dtos import (
    DragonTigerItemDTO,
    SectorCapitalFlowItemDTO,
)
from src.modules.market_insight.domain.ports.capital_flow_data_port import ICapitalFlowDataPort


class DeCapitalFlowDataAdapter(ICapitalFlowDataPort):
    """
    DE 资金流向数据适配器（MI 基础设施层）
    实现 ICapitalFlowDataPort 接口，桥接 DataEngineering 模块
    将 DE 领域实体转换为 MI 领域层 DTO
    """

    def __init__(
        self,
        dragon_tiger_use_case: GetDragonTigerByDateUseCase,
        sector_capital_flow_use_case: GetSectorCapitalFlowByDateUseCase,
    ):
        self.dragon_tiger_use_case = dragon_tiger_use_case
        self.sector_capital_flow_use_case = sector_capital_flow_use_case

    async def get_dragon_tiger(self, trade_date: date) -> list[DragonTigerItemDTO]:
        """
        获取指定日期的龙虎榜详情
        """
        entities = await self.dragon_tiger_use_case.execute(trade_date)

        return [
            DragonTigerItemDTO(
                third_code=entity.third_code,
                stock_name=entity.stock_name,
                pct_chg=entity.pct_chg,
                close=entity.close,
                reason=entity.reason,
                net_amount=entity.net_amount,
                buy_amount=entity.buy_amount,
                sell_amount=entity.sell_amount,
                buy_seats=entity.buy_seats,
                sell_seats=entity.sell_seats,
            )
            for entity in entities
        ]

    async def get_sector_capital_flow(
        self, trade_date: date, sector_type: str | None = None
    ) -> list[SectorCapitalFlowItemDTO]:
        """
        获取指定日期的板块资金流向
        """
        entities = await self.sector_capital_flow_use_case.execute(trade_date, sector_type)

        return [
            SectorCapitalFlowItemDTO(
                sector_name=entity.sector_name,
                sector_type=entity.sector_type,
                net_amount=entity.net_amount,
                inflow_amount=entity.inflow_amount,
                outflow_amount=entity.outflow_amount,
                pct_chg=entity.pct_chg,
            )
            for entity in entities
        ]
