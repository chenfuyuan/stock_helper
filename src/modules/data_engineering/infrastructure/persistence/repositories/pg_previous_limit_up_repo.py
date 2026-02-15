from datetime import date

from loguru import logger
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from src.modules.data_engineering.domain.model.previous_limit_up import PreviousLimitUpStock
from src.modules.data_engineering.domain.ports.repositories.previous_limit_up_repo import (
    IPreviousLimitUpRepository,
)
from src.modules.data_engineering.infrastructure.persistence.models.previous_limit_up_model import (
    PreviousLimitUpModel,
)
from src.shared.infrastructure.base_repository import BaseRepository


class PgPreviousLimitUpRepository(
    BaseRepository[PreviousLimitUpModel], IPreviousLimitUpRepository
):
    """
    PostgreSQL 昨日涨停表现数据仓储实现
    实现 IPreviousLimitUpRepository 接口
    """

    def __init__(self, session):
        super().__init__(PreviousLimitUpModel, session)

    async def save_all(self, stocks: list[PreviousLimitUpStock]) -> int:
        """
        批量 UPSERT 昨日涨停表现记录（以 trade_date + third_code 为唯一键）
        """
        if not stocks:
            return 0

        stock_dicts = [stock.model_dump(exclude={"id"}, exclude_unset=True) for stock in stocks]

        stmt = insert(PreviousLimitUpModel).values(stock_dicts)
        stmt = stmt.on_conflict_do_update(
            index_elements=["trade_date", "third_code"],
            set_={
                "stock_name": stmt.excluded.stock_name,
                "pct_chg": stmt.excluded.pct_chg,
                "close": stmt.excluded.close,
                "amount": stmt.excluded.amount,
                "turnover_rate": stmt.excluded.turnover_rate,
                "yesterday_consecutive_boards": stmt.excluded.yesterday_consecutive_boards,
                "industry": stmt.excluded.industry,
                "updated_at": stmt.excluded.updated_at,
            },
        )

        await self.session.execute(stmt)
        await self.session.commit()

        count = len(stocks)
        logger.debug(f"UPSERT {count} 条昨日涨停表现记录")
        return count

    async def get_by_date(self, trade_date: date) -> list[PreviousLimitUpStock]:
        """
        查询指定日期的昨日涨停表现记录
        """
        stmt = select(PreviousLimitUpModel).where(
            PreviousLimitUpModel.trade_date == trade_date
        )
        result = await self.session.execute(stmt)
        models = result.scalars().all()

        import uuid
        return [
            PreviousLimitUpStock(
                id=uuid.UUID(int=model.id),  # 将整数ID转换为UUID
                trade_date=model.trade_date,
                third_code=model.third_code,
                stock_name=model.stock_name,
                pct_chg=model.pct_chg,
                close=model.close,
                amount=model.amount,
                turnover_rate=model.turnover_rate,
                yesterday_consecutive_boards=model.yesterday_consecutive_boards,
                industry=model.industry,
                created_at=model.created_at,
                updated_at=model.updated_at,
            )
            for model in models
        ]
