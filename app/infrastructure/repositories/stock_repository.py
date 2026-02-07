from typing import List, Optional
from sqlalchemy.future import select
from sqlalchemy.dialects.postgresql import insert
from app.infrastructure.base_repository import BaseRepository
from app.domain.stock.entity import StockInfo
from app.domain.stock.repository import StockRepository
from app.infrastructure.db.models.stock import StockModel

class StockRepositoryImpl(BaseRepository[StockModel], StockRepository):
    """
    股票仓储实现
    Stock Repository Implementation
    """
    def __init__(self, session):
        super().__init__(StockModel, session)

    async def get_by_symbol(self, symbol: str) -> Optional[StockInfo]:
        """根据股票代码查询"""
        result = await self.session.execute(
            select(StockModel).where(StockModel.symbol == symbol)
        )
        model = result.scalar_one_or_none()
        return StockInfo.model_validate(model) if model else None

    async def get_by_third_code(self, third_code: str) -> Optional[StockInfo]:
        """根据第三方代码查询"""
        result = await self.session.execute(
            select(StockModel).where(StockModel.third_code == third_code)
        )
        model = result.scalar_one_or_none()
        return StockInfo.model_validate(model) if model else None

    async def save(self, stock: StockInfo) -> StockInfo:
        """保存单个股票信息 (Create or Update)"""
        # 转换为字典并移除 None 值
        stock_data = stock.model_dump(exclude_unset=True)
        
        stmt = insert(StockModel).values(**stock_data)
        stmt = stmt.on_conflict_do_update(
            index_elements=['third_code'],
            set_=stock_data
        ).returning(StockModel)
        
        result = await self.session.execute(stmt)
        await self.session.commit()
        return StockInfo.model_validate(result.scalar_one())

    async def save_all(self, stocks: List[StockInfo]) -> List[StockInfo]:
        """批量保存股票信息"""
        if not stocks:
            return []
            
        stock_data_list = [s.model_dump(exclude_unset=True) for s in stocks]
        
        # 分批处理，避免参数过多导致 SQL 错误
        batch_size = 1000
        saved_stocks = []
        
        for i in range(0, len(stock_data_list), batch_size):
            batch = stock_data_list[i:i + batch_size]
            
            stmt = insert(StockModel).values(batch)
            stmt = stmt.on_conflict_do_update(
                index_elements=['third_code'],
                set_={col.name: col for col in stmt.excluded if col.name not in ['id', 'created_at']}
            ).returning(StockModel)
            
            result = await self.session.execute(stmt)
            # 立即转换为领域对象，避免 Session 提交后对象过期
            batch_results = [StockInfo.model_validate(row) for row in result.scalars().all()]
            saved_stocks.extend(batch_results)
        
        await self.session.commit()
        
        return saved_stocks
