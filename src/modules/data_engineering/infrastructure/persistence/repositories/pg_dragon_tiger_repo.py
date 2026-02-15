from datetime import date

from loguru import logger
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from src.modules.data_engineering.domain.model.dragon_tiger import DragonTigerDetail
from src.modules.data_engineering.domain.ports.repositories.dragon_tiger_repo import (
    IDragonTigerRepository,
)
from src.modules.data_engineering.infrastructure.persistence.models.dragon_tiger_model import (
    DragonTigerModel,
)
from src.shared.infrastructure.base_repository import BaseRepository


class PgDragonTigerRepository(BaseRepository[DragonTigerModel], IDragonTigerRepository):
    """
    PostgreSQL 龙虎榜数据仓储实现
    实现 IDragonTigerRepository 接口
    """

    def __init__(self, session):
        super().__init__(DragonTigerModel, session)

    async def save_all(self, details: list[DragonTigerDetail]) -> int:
        """
        批量 UPSERT 龙虎榜记录（以 trade_date + third_code + reason 为唯一键）
        """
        if not details:
            return 0

        detail_dicts = [
            detail.model_dump(exclude={"id"}, exclude_unset=True) for detail in details
        ]

        stmt = insert(DragonTigerModel).values(detail_dicts)
        stmt = stmt.on_conflict_do_update(
            index_elements=["trade_date", "third_code", "reason"],
            set_={
                "stock_name": stmt.excluded.stock_name,
                "pct_chg": stmt.excluded.pct_chg,
                "close": stmt.excluded.close,
                "net_amount": stmt.excluded.net_amount,
                "buy_amount": stmt.excluded.buy_amount,
                "sell_amount": stmt.excluded.sell_amount,
                "buy_seats": stmt.excluded.buy_seats,
                "sell_seats": stmt.excluded.sell_seats,
                "updated_at": stmt.excluded.updated_at,
            },
        )

        await self.session.execute(stmt)
        await self.session.commit()

        count = len(details)
        logger.debug(f"UPSERT {count} 条龙虎榜记录")
        return count

    async def get_by_date(self, trade_date: date) -> list[DragonTigerDetail]:
        """
        查询指定日期的龙虎榜记录
        """
        stmt = select(DragonTigerModel).where(DragonTigerModel.trade_date == trade_date)
        result = await self.session.execute(stmt)
        models = result.scalars().all()

        import uuid
        return [
            DragonTigerDetail(
                id=uuid.UUID(int=model.id),  # 将整数ID转换为UUID
                trade_date=model.trade_date,
                third_code=model.third_code,
                stock_name=model.stock_name,
                pct_chg=model.pct_chg,
                close=model.close,
                reason=model.reason,
                net_amount=model.net_amount,
                buy_amount=model.buy_amount,
                sell_amount=model.sell_amount,
                buy_seats=model.buy_seats,
                sell_seats=model.sell_seats,
                created_at=model.created_at,
                updated_at=model.updated_at,
            )
            for model in models
        ]
