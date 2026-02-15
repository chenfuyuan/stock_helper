from datetime import date

from loguru import logger
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from src.modules.data_engineering.domain.model.broken_board import BrokenBoardStock
from src.modules.data_engineering.domain.ports.repositories.broken_board_repo import (
    IBrokenBoardRepository,
)
from src.modules.data_engineering.infrastructure.persistence.models.broken_board_model import (
    BrokenBoardModel,
)
from src.shared.infrastructure.base_repository import BaseRepository


class PgBrokenBoardRepository(BaseRepository[BrokenBoardModel], IBrokenBoardRepository):
    """
    PostgreSQL 炸板池数据仓储实现
    实现 IBrokenBoardRepository 接口
    """

    def __init__(self, session):
        super().__init__(BrokenBoardModel, session)

    async def save_all(self, stocks: list[BrokenBoardStock]) -> int:
        """
        批量 UPSERT 炸板池记录（以 trade_date + third_code 为唯一键）
        """
        if not stocks:
            return 0

        stock_dicts = [stock.model_dump(exclude={"id"}, exclude_unset=True) for stock in stocks]

        stmt = insert(BrokenBoardModel).values(stock_dicts)
        stmt = stmt.on_conflict_do_update(
            index_elements=["trade_date", "third_code"],
            set_={
                "stock_name": stmt.excluded.stock_name,
                "pct_chg": stmt.excluded.pct_chg,
                "close": stmt.excluded.close,
                "amount": stmt.excluded.amount,
                "turnover_rate": stmt.excluded.turnover_rate,
                "open_count": stmt.excluded.open_count,
                "first_limit_up_time": stmt.excluded.first_limit_up_time,
                "last_open_time": stmt.excluded.last_open_time,
                "industry": stmt.excluded.industry,
                "updated_at": stmt.excluded.updated_at,
            },
        )

        await self.session.execute(stmt)
        await self.session.commit()

        count = len(stocks)
        logger.debug(f"UPSERT {count} 条炸板池记录")
        return count

    async def get_by_date(self, trade_date: date) -> list[BrokenBoardStock]:
        """
        查询指定日期的炸板池记录
        """
        stmt = select(BrokenBoardModel).where(BrokenBoardModel.trade_date == trade_date)
        result = await self.session.execute(stmt)
        models = result.scalars().all()

        import uuid
        return [
            BrokenBoardStock(
                id=uuid.UUID(int=model.id),  # 将整数ID转换为UUID
                trade_date=model.trade_date,
                third_code=model.third_code,
                stock_name=model.stock_name,
                pct_chg=model.pct_chg,
                close=model.close,
                amount=model.amount,
                turnover_rate=model.turnover_rate,
                open_count=model.open_count,
                first_limit_up_time=model.first_limit_up_time,
                last_open_time=model.last_open_time,
                industry=model.industry,
                created_at=model.created_at,
                updated_at=model.updated_at,
            )
            for model in models
        ]
