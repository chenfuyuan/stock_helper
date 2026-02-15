"""
概念热度 PostgreSQL Repository 实现
"""

from datetime import date
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.market_insight.domain.model.concept_heat import ConceptHeat
from src.modules.market_insight.domain.ports.repositories.concept_heat_repo import (
    IConceptHeatRepository,
)
from src.modules.market_insight.infrastructure.persistence.models.concept_heat_model import (
    ConceptHeatModel,
)


class PgConceptHeatRepository(IConceptHeatRepository):
    """概念热度 PostgreSQL Repository"""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def save_all(self, heats: List[ConceptHeat]) -> int:
        """
        批量 UPSERT 概念热度数据
        :param heats: 概念热度实体列表
        :return: 影响行数
        """
        if not heats:
            return 0

        data_list = [
            {
                "trade_date": h.trade_date,
                "concept_code": h.concept_code,
                "concept_name": h.concept_name,
                "avg_pct_chg": h.avg_pct_chg,
                "stock_count": h.stock_count,
                "up_count": h.up_count,
                "down_count": h.down_count,
                "limit_up_count": h.limit_up_count,
                "total_amount": h.total_amount,
            }
            for h in heats
        ]

        stmt = insert(ConceptHeatModel).values(data_list)
        stmt = stmt.on_conflict_do_update(
            index_elements=["trade_date", "concept_code"],
            set_={
                "concept_name": stmt.excluded.concept_name,
                "avg_pct_chg": stmt.excluded.avg_pct_chg,
                "stock_count": stmt.excluded.stock_count,
                "up_count": stmt.excluded.up_count,
                "down_count": stmt.excluded.down_count,
                "limit_up_count": stmt.excluded.limit_up_count,
                "total_amount": stmt.excluded.total_amount,
            },
        )

        await self._session.execute(stmt)
        await self._session.commit()
        return len(heats)

    async def get_by_date(
        self, trade_date: date, top_n: Optional[int] = None
    ) -> List[ConceptHeat]:
        """
        查询指定日期的板块热度
        :param trade_date: 交易日期
        :param top_n: 仅返回前 N 条，None 表示返回全部
        :return: 概念热度列表，按 avg_pct_chg 降序
        """
        stmt = (
            select(ConceptHeatModel)
            .where(ConceptHeatModel.trade_date == trade_date)
            .order_by(ConceptHeatModel.avg_pct_chg.desc())
        )

        if top_n is not None:
            stmt = stmt.limit(top_n)

        result = await self._session.execute(stmt)
        rows = result.scalars().all()

        return [
            ConceptHeat(
                trade_date=r.trade_date,
                concept_code=r.concept_code,
                concept_name=r.concept_name,
                avg_pct_chg=r.avg_pct_chg,
                stock_count=r.stock_count,
                up_count=r.up_count,
                down_count=r.down_count,
                limit_up_count=r.limit_up_count,
                total_amount=r.total_amount,
            )
            for r in rows
        ]

    async def get_by_concept_and_date_range(
        self, concept_code: str, start_date: date, end_date: date
    ) -> List[ConceptHeat]:
        """
        查询指定概念在日期范围内的热度历史
        :param concept_code: 概念代码
        :param start_date: 开始日期
        :param end_date: 结束日期
        :return: 概念热度历史列表
        """
        stmt = (
            select(ConceptHeatModel)
            .where(
                ConceptHeatModel.concept_code == concept_code,
                ConceptHeatModel.trade_date >= start_date,
                ConceptHeatModel.trade_date <= end_date,
            )
            .order_by(ConceptHeatModel.trade_date.asc())
        )

        result = await self._session.execute(stmt)
        rows = result.scalars().all()

        return [
            ConceptHeat(
                trade_date=r.trade_date,
                concept_code=r.concept_code,
                concept_name=r.concept_name,
                avg_pct_chg=r.avg_pct_chg,
                stock_count=r.stock_count,
                up_count=r.up_count,
                down_count=r.down_count,
                limit_up_count=r.limit_up_count,
                total_amount=r.total_amount,
            )
            for r in rows
        ]
