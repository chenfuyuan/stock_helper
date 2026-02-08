from typing import List
from sqlalchemy.dialects.postgresql import insert
from app.infrastructure.base_repository import BaseRepository
from app.domain.stock.entities import StockFinance
from app.domain.stock.repository import StockFinanceRepository
from app.infrastructure.db.models.stock_finance import StockFinanceModel

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
        
        # Batch processing
        batch_size = 1000
        total_saved = 0
        
        for i in range(0, len(data_list), batch_size):
            batch = data_list[i:i + batch_size]
            
            stmt = insert(StockFinanceModel).values(batch)
            stmt = stmt.on_conflict_do_update(
                index_elements=['third_code', 'ann_date', 'end_date'],
                set_={col.name: col for col in stmt.excluded if col.name not in ['created_at']}
            )
            
            await self.session.execute(stmt)
            total_saved += len(batch)
            
        await self.session.commit()
        return total_saved
