from datetime import date

from loguru import logger
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from src.modules.data_engineering.domain.model.limit_up_pool import LimitUpPoolStock
from src.modules.data_engineering.domain.ports.repositories.limit_up_pool_repo import (
    ILimitUpPoolRepository,
)
from src.modules.data_engineering.infrastructure.persistence.models.limit_up_pool_model import (
    LimitUpPoolModel,
)
from src.shared.infrastructure.base_repository import BaseRepository


class PgLimitUpPoolRepository(BaseRepository[LimitUpPoolModel], ILimitUpPoolRepository):
    """
    PostgreSQL 涨停池数据仓储实现
    实现 ILimitUpPoolRepository 接口
    """

    def __init__(self, session):
        super().__init__(LimitUpPoolModel, session)

    async def save_all(self, stocks: list[LimitUpPoolStock]) -> int:
        """
        批量 UPSERT 涨停池记录（以 trade_date + third_code 为唯一键）
        使用 PostgreSQL ON CONFLICT DO UPDATE 实现幂等写入
        """
        if not stocks:
            return 0

        stock_dicts = [stock.model_dump(exclude={"id"}, exclude_unset=True) for stock in stocks]

        stmt = insert(LimitUpPoolModel).values(stock_dicts)
        stmt = stmt.on_conflict_do_update(
            index_elements=["trade_date", "third_code"],
            set_={
                "stock_name": stmt.excluded.stock_name,
                "pct_chg": stmt.excluded.pct_chg,
                "close": stmt.excluded.close,
                "amount": stmt.excluded.amount,
                "turnover_rate": stmt.excluded.turnover_rate,
                "consecutive_boards": stmt.excluded.consecutive_boards,
                "first_limit_up_time": stmt.excluded.first_limit_up_time,
                "last_limit_up_time": stmt.excluded.last_limit_up_time,
                "industry": stmt.excluded.industry,
                "updated_at": stmt.excluded.updated_at,
            },
        )

        await self.session.execute(stmt)
        await self.session.commit()

        count = len(stocks)
        logger.debug(f"UPSERT {count} 条涨停池记录")
        return count

    async def get_by_date(self, trade_date: date) -> list[LimitUpPoolStock]:
        """
        查询指定日期的涨停池记录
        """
        stmt = select(LimitUpPoolModel).where(LimitUpPoolModel.trade_date == trade_date)
        result = await self.session.execute(stmt)
        models = result.scalars().all()

        import uuid
        return [
            LimitUpPoolStock(
                id=uuid.UUID(int=model.id),  # 将整数ID转换为UUID
                trade_date=model.trade_date,
                third_code=model.third_code,
                stock_name=model.stock_name,
                pct_chg=model.pct_chg,
                close=model.close,
                amount=model.amount,
                turnover_rate=model.turnover_rate,
                consecutive_boards=model.consecutive_boards,
                first_limit_up_time=model.first_limit_up_time,
                last_limit_up_time=model.last_limit_up_time,
                industry=model.industry,
                created_at=model.created_at,
                updated_at=model.updated_at,
            )
            for model in models
        ]
