from typing import List
from sqlalchemy.dialects.postgresql import insert
from src.shared.infrastructure.base_repository import BaseRepository
from src.modules.data_engineering.domain.model.daily_bar import StockDaily
from src.modules.data_engineering.domain.ports.repositories.market_quote_repo import IMarketQuoteRepository
from src.modules.data_engineering.infrastructure.persistence.models.daily_bar_model import StockDailyModel

class StockDailyRepositoryImpl(BaseRepository[StockDailyModel], IMarketQuoteRepository):
    def __init__(self, session):
        super().__init__(StockDailyModel, session)

    async def save_all(self, dailies: List[StockDaily]) -> int:
        if not dailies:
            return 0
            
        # Convert to dicts first
        raw_data_list = [d.model_dump(exclude_unset=True) for d in dailies]
        
        # Deduplicate based on primary key (third_code, trade_date)
        # Keep the last entry if duplicates exist
        deduplicated_data = {}
        for item in raw_data_list:
            key = (item.get('third_code'), item.get('trade_date'))
            deduplicated_data[key] = item
            
        data_list = list(deduplicated_data.values())
        
        # Batch processing
        batch_size = 1000
        total_saved = 0
        
        for i in range(0, len(data_list), batch_size):
            batch = data_list[i:i + batch_size]
            
            stmt = insert(StockDailyModel).values(batch)
            stmt = stmt.on_conflict_do_update(
                index_elements=['third_code', 'trade_date'],
                set_={col.name: col for col in stmt.excluded if col.name not in ['created_at']}
            )
            
            await self.session.execute(stmt)
            total_saved += len(batch)
            
        await self.session.commit()
        return total_saved
