"""
涨停股 PostgreSQL Repository 实现
"""

from datetime import date
from typing import List

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.market_insight.domain.model.enums import LimitType
from src.modules.market_insight.domain.model.limit_up_stock import LimitUpStock, Concept
from src.modules.market_insight.domain.ports.repositories.limit_up_repo import (
    ILimitUpRepository,
)
from src.modules.market_insight.infrastructure.persistence.models.limit_up_stock_model import (
    LimitUpStockModel,
)


class PgLimitUpRepository(ILimitUpRepository):
    """涨停股 PostgreSQL Repository"""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def save_all(self, stocks: List[LimitUpStock]) -> int:
        """
        批量 UPSERT 涨停股数据
        :param stocks: 涨停股实体列表
        :return: 影响行数
        """
        if not stocks:
            return 0

        data_list = [
            {
                "trade_date": s.trade_date,
                "third_code": s.third_code,
                "stock_name": s.stock_name,
                "pct_chg": s.pct_chg,
                "close": s.close,
                "amount": s.amount,
                "concepts": [c.model_dump() for c in s.concepts],
                "limit_type": s.limit_type.value,
            }
            for s in stocks
        ]

        stmt = insert(LimitUpStockModel).values(data_list)
        stmt = stmt.on_conflict_do_update(
            index_elements=["trade_date", "third_code"],
            set_={
                "stock_name": stmt.excluded.stock_name,
                "pct_chg": stmt.excluded.pct_chg,
                "close": stmt.excluded.close,
                "amount": stmt.excluded.amount,
                "concepts": stmt.excluded.concepts,
                "limit_type": stmt.excluded.limit_type,
            },
        )

        await self._session.execute(stmt)
        await self._session.commit()
        return len(stocks)

    async def get_by_date(self, trade_date: date) -> List[LimitUpStock]:
        """
        查询指定日期的所有涨停股
        :param trade_date: 交易日期
        :return: 涨停股列表
        """
        stmt = (
            select(LimitUpStockModel)
            .where(LimitUpStockModel.trade_date == trade_date)
            .order_by(LimitUpStockModel.pct_chg.desc())
        )

        result = await self._session.execute(stmt)
        rows = result.scalars().all()

        return [
            LimitUpStock(
                trade_date=r.trade_date,
                third_code=r.third_code,
                stock_name=r.stock_name,
                pct_chg=r.pct_chg,
                close=r.close,
                amount=r.amount,
                concepts=[Concept(**c) for c in (r.concepts or [])],
                limit_type=LimitType(r.limit_type),
            )
            for r in rows
        ]

    async def get_by_date_and_concept(
        self, trade_date: date, concept_code: str
    ) -> List[LimitUpStock]:
        """
        查询指定日期、指定概念下的涨停股
        :param trade_date: 交易日期
        :param concept_code: 概念代码
        :return: 涨停股列表
        """
        stmt = (
            select(LimitUpStockModel)
            .where(
                LimitUpStockModel.trade_date == trade_date,
                LimitUpStockModel.concepts.op('@>')([{'code': concept_code}]),
            )
            .order_by(LimitUpStockModel.pct_chg.desc())
        )

        result = await self._session.execute(stmt)
        rows = result.scalars().all()

        return [
            LimitUpStock(
                trade_date=r.trade_date,
                third_code=r.third_code,
                stock_name=r.stock_name,
                pct_chg=r.pct_chg,
                close=r.close,
                amount=r.amount,
                concepts=[Concept(**c) for c in (r.concepts or [])],
                limit_type=LimitType(r.limit_type),
            )
            for r in rows
        ]
