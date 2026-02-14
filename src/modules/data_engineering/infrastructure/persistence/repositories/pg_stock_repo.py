from datetime import date, datetime
from typing import List, Optional

from sqlalchemy import and_, or_, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.future import select

from src.modules.data_engineering.domain.model.stock import StockInfo
from src.modules.data_engineering.domain.ports.repositories.stock_basic_repo import (
    IStockBasicRepository,
)
from src.modules.data_engineering.infrastructure.persistence.models.finance_model import (
    StockFinanceModel,
)
from src.modules.data_engineering.infrastructure.persistence.models.stock_model import (
    StockModel,
)
from src.shared.infrastructure.base_repository import BaseRepository


class StockRepositoryImpl(BaseRepository[StockModel], IStockBasicRepository):
    """
    股票仓储实现
    Stock Repository Implementation
    """

    def __init__(self, session):
        super().__init__(StockModel, session)

    async def get_missing_finance_stocks(
        self, target_period: str, check_threshold_date: date, limit: int = 200
    ) -> List[str]:
        """
        获取缺少指定报告期财务数据的股票代码列表
        """
        # 转换 target_period 字符串 (YYYYMMDD) 为 date 对象
        try:
            target_date = datetime.strptime(target_period, "%Y%m%d").date()
        except ValueError:
            target_date = target_period

        # 子查询：已拥有目标报告期数据的股票
        subquery = select(StockFinanceModel.third_code).where(
            StockFinanceModel.end_date == target_date
        )

        stmt = (
            select(StockModel.third_code)
            .where(
                and_(
                    StockModel.third_code.not_in(subquery),
                    or_(
                        StockModel.last_finance_sync_date is None,
                        StockModel.last_finance_sync_date < check_threshold_date,
                    ),
                )
            )
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_last_finance_sync_date(self, third_codes: List[str], sync_date: date) -> None:
        """
        批量更新最后财务同步时间
        """
        if not third_codes:
            return

        stmt = (
            update(StockModel)
            .where(StockModel.third_code.in_(third_codes))
            .values(last_finance_sync_date=sync_date)
        )

        await self.session.execute(stmt)
        await self.session.commit()

    async def get_by_symbol(self, symbol: str) -> Optional[StockInfo]:
        """根据股票代码查询"""
        result = await self.session.execute(select(StockModel).where(StockModel.symbol == symbol))
        model = result.scalar_one_or_none()
        return StockInfo.model_validate(model) if model else None

    async def get_by_third_code(self, third_code: str) -> Optional[StockInfo]:
        """根据第三方代码查询"""
        result = await self.session.execute(
            select(StockModel).where(StockModel.third_code == third_code)
        )
        model = result.scalar_one_or_none()
        return StockInfo.model_validate(model) if model else None

    async def get_by_third_codes(self, third_codes: List[str]) -> List[StockInfo]:
        """根据第三方代码批量查询"""
        if not third_codes:
            return []

        result = await self.session.execute(
            select(StockModel).where(StockModel.third_code.in_(third_codes))
        )
        return [StockInfo.model_validate(model) for model in result.scalars().all()]

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[StockInfo]:
        """获取所有股票（支持分页）"""
        result = await self.session.execute(select(StockModel).offset(skip).limit(limit))
        return [StockInfo.model_validate(model) for model in result.scalars().all()]

    async def save(self, stock: StockInfo) -> StockInfo:
        """保存单个股票信息 (Create or Update)"""
        stock_data = stock.model_dump(exclude_unset=True)

        stmt = insert(StockModel).values(**stock_data)
        stmt = stmt.on_conflict_do_update(index_elements=["third_code"], set_=stock_data).returning(
            StockModel
        )

        result = await self.session.execute(stmt)
        await self.session.commit()
        return StockInfo.model_validate(result.scalar_one())

    async def save_all(self, stocks: List[StockInfo]) -> List[StockInfo]:
        """批量保存股票信息"""
        if not stocks:
            return []

        stock_data_list = [s.model_dump(exclude_unset=True) for s in stocks]

        batch_size = 1000
        saved_stocks = []

        for i in range(0, len(stock_data_list), batch_size):
            batch = stock_data_list[i : i + batch_size]

            stmt = insert(StockModel).values(batch)
            stmt = stmt.on_conflict_do_update(
                index_elements=["third_code"],
                set_={
                    col.name: col for col in stmt.excluded if col.name not in ["id", "created_at"]
                },
            ).returning(StockModel)

            result = await self.session.execute(stmt)
            batch_results = [StockInfo.model_validate(row) for row in result.scalars().all()]
            saved_stocks.extend(batch_results)

        await self.session.commit()

        return saved_stocks
