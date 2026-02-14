from typing import List

from sqlalchemy import select

from src.modules.data_engineering.domain.model.financial_report import (
    StockFinance,
)
from src.modules.data_engineering.domain.ports.repositories.financial_data_repo import (
    IFinancialDataRepository,
)
from src.modules.data_engineering.infrastructure.persistence.models.finance_model import (
    StockFinanceModel,
)
from src.shared.infrastructure.base_repository import BaseRepository


class StockFinanceRepositoryImpl(
    BaseRepository[StockFinanceModel], IFinancialDataRepository
):
    def __init__(self, session):
        super().__init__(StockFinanceModel, session)

    async def save_all(self, finances: List[StockFinance]) -> int:
        if not finances:
            return 0

        # Convert to dicts first
        raw_data_list = [f.model_dump(exclude_unset=True) for f in finances]

        # Deduplicate based on primary key (third_code, ann_date, end_date)
        # Keep the last entry if duplicates exist
        deduplicated_data = {}
        for item in raw_data_list:
            key = (
                item.get("third_code"),
                item.get("ann_date"),
                item.get("end_date"),
            )
            deduplicated_data[key] = item

        data_list = list(deduplicated_data.values())

        # 使用基类的 upsert_all 方法，简化代码并提升性能
        return await self.upsert_all(
            items=data_list,
            unique_fields=["third_code", "ann_date", "end_date"],
        )

    async def get_by_third_code_recent(
        self, third_code: str, limit: int
    ) -> List[StockFinance]:
        """按第三方代码查询最近 N 期财务记录，按 end_date 降序返回。"""
        stmt = (
            select(StockFinanceModel)
            .where(StockFinanceModel.third_code == third_code)
            .order_by(StockFinanceModel.end_date.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        rows = result.scalars().all()
        return [StockFinance.model_validate(r) for r in rows]
