from typing import List
from src.shared.infrastructure.base_repository import BaseRepository
from src.modules.market_data.domain.entities import StockFinance
from src.modules.market_data.domain.repositories import StockFinanceRepository
from src.modules.market_data.infrastructure.adapters.persistence.models.stock_finance import StockFinanceModel

class StockFinanceRepositoryImpl(BaseRepository[StockFinanceModel], StockFinanceRepository):
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
            key = (item.get('third_code'), item.get('ann_date'), item.get('end_date'))
            deduplicated_data[key] = item
            
        data_list = list(deduplicated_data.values())
        
        # 使用基类的 upsert_all 方法，简化代码并提升性能
        return await self.upsert_all(
            items=data_list,
            unique_fields=['third_code', 'ann_date', 'end_date']
        )
