from typing import List, Optional
from sqlalchemy.future import select
from sqlalchemy.dialects.postgresql import insert
from app.infrastructure.base_repository import BaseRepository
from app.domain.stock.entities import StockInfo
from app.domain.stock.repository import StockRepository
from app.infrastructure.db.models.stock_info import StockModel

from datetime import date, datetime
from sqlalchemy import update, and_, or_, not_
from app.infrastructure.db.models.stock_finance import StockFinanceModel

class StockRepositoryImpl(BaseRepository[StockModel], StockRepository):
    """
    股票仓储实现
    Stock Repository Implementation
    """
    def __init__(self, session):
        super().__init__(StockModel, session)

    async def get_missing_finance_stocks(self, target_period: str, check_threshold_date: date, limit: int = 200) -> List[str]:
        """
        获取缺少指定报告期财务数据的股票代码列表
        """
        # 转换 target_period 字符串 (YYYYMMDD) 为 date 对象
        try:
            target_date = datetime.strptime(target_period, "%Y%m%d").date()
        except ValueError:
            # 如果格式不对，尝试直接使用（可能调用者已经传了标准格式，或者作为字符串处理）
            # 但针对 Date 类型列，最好是 date 对象
            target_date = target_period

        # 子查询：已拥有目标报告期数据的股票
        subquery = select(StockFinanceModel.third_code).where(StockFinanceModel.end_date == target_date)
        
        stmt = select(StockModel.third_code).where(
            and_(
                StockModel.third_code.not_in(subquery),

                or_(
                    StockModel.last_finance_sync_date == None,
                    StockModel.last_finance_sync_date < check_threshold_date
                )
            )
        ).limit(limit)
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


    async def update_last_finance_sync_date(self, third_codes: List[str], sync_date: date) -> None:
        """
        批量更新最后财务同步时间
        注意：此方法会立即 commit，如果需要作为事务的一部分，请谨慎调用或修改为不自动 commit
        """
        if not third_codes:
            return
            
        stmt = update(StockModel).where(
            StockModel.third_code.in_(third_codes)
        ).values(last_finance_sync_date=sync_date)
        
        await self.session.execute(stmt)
        await self.session.commit()

    async def update_last_finance_sync_date_single(self, third_code: str, sync_date: date) -> None:
        """更新单个股票最后财务同步时间"""
        stmt = update(StockModel).where(
            StockModel.third_code == third_code
        ).values(last_finance_sync_date=sync_date)
        
        await self.session.execute(stmt)
        await self.session.commit()


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
        # 复用 BaseRepository 的 get_all，它已经支持 skip/limit
        # 但 BaseRepository 返回的是 Model，我们需要转为 Entity
        # 这里重写以优化或明确逻辑
        result = await self.session.execute(
            select(StockModel).offset(skip).limit(limit)
        )
        return [StockInfo.model_validate(model) for model in result.scalars().all()]

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
