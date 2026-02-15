from datetime import date

from loguru import logger
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from src.modules.data_engineering.domain.model.sector_capital_flow import SectorCapitalFlow
from src.modules.data_engineering.domain.ports.repositories.sector_capital_flow_repo import (
    ISectorCapitalFlowRepository,
)
from src.modules.data_engineering.infrastructure.persistence.models.sector_capital_flow_model import (
    SectorCapitalFlowModel,
)
from src.shared.infrastructure.base_repository import BaseRepository


class PgSectorCapitalFlowRepository(
    BaseRepository[SectorCapitalFlowModel], ISectorCapitalFlowRepository
):
    """
    PostgreSQL 板块资金流向数据仓储实现
    实现 ISectorCapitalFlowRepository 接口
    """

    def __init__(self, session):
        super().__init__(SectorCapitalFlowModel, session)

    async def save_all(self, flows: list[SectorCapitalFlow]) -> int:
        """
        批量 UPSERT 板块资金流向记录（以 trade_date + sector_name + sector_type 为唯一键）
        """
        if not flows:
            return 0

        flow_dicts = [flow.model_dump(exclude={"id"}, exclude_unset=True) for flow in flows]

        stmt = insert(SectorCapitalFlowModel).values(flow_dicts)
        stmt = stmt.on_conflict_do_update(
            index_elements=["trade_date", "sector_name", "sector_type"],
            set_={
                "net_amount": stmt.excluded.net_amount,
                "inflow_amount": stmt.excluded.inflow_amount,
                "outflow_amount": stmt.excluded.outflow_amount,
                "pct_chg": stmt.excluded.pct_chg,
                "updated_at": stmt.excluded.updated_at,
            },
        )

        await self.session.execute(stmt)
        await self.session.commit()

        count = len(flows)
        logger.debug(f"UPSERT {count} 条板块资金流向记录")
        return count

    async def get_by_date(
        self, trade_date: date, sector_type: str | None = None
    ) -> list[SectorCapitalFlow]:
        """
        查询指定日期的板块资金流向记录
        """
        stmt = select(SectorCapitalFlowModel).where(
            SectorCapitalFlowModel.trade_date == trade_date
        )

        if sector_type:
            stmt = stmt.where(SectorCapitalFlowModel.sector_type == sector_type)

        result = await self.session.execute(stmt)
        models = result.scalars().all()

        import uuid
        return [
            SectorCapitalFlow(
                id=uuid.UUID(int=model.id),  # 将整数ID转换为UUID
                trade_date=model.trade_date,
                sector_name=model.sector_name,
                sector_type=model.sector_type,
                net_amount=model.net_amount,
                inflow_amount=model.inflow_amount,
                outflow_amount=model.outflow_amount,
                pct_chg=model.pct_chg,
                created_at=model.created_at,
                updated_at=model.updated_at,
            )
            for model in models
        ]
