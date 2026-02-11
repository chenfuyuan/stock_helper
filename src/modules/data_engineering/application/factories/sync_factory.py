from typing import AsyncGenerator
from contextlib import asynccontextmanager

from src.shared.infrastructure.db.session import AsyncSessionLocal
from src.modules.data_engineering.application.commands.sync_engine import SyncEngine
from src.modules.data_engineering.application.commands.sync_incremental_finance_data import SyncIncrementalFinanceDataUseCase
from src.modules.data_engineering.infrastructure.persistence.repositories.pg_sync_task_repo import SyncTaskRepositoryImpl
from src.modules.data_engineering.infrastructure.persistence.repositories.pg_stock_repo import StockRepositoryImpl
from src.modules.data_engineering.infrastructure.persistence.repositories.pg_quote_repo import StockDailyRepositoryImpl
from src.modules.data_engineering.infrastructure.persistence.repositories.pg_finance_repo import StockFinanceRepositoryImpl
from src.modules.data_engineering.infrastructure.external_apis.tushare.client import TushareClient


class SyncUseCaseFactory:
    """
    同步用例工厂
    
    封装依赖注入和 session 管理，供 Presentation 层使用。
    避免 Presentation 层直接依赖 Infrastructure 层的具体实现。
    """
    
    @staticmethod
    @asynccontextmanager
    async def create_sync_engine() -> AsyncGenerator[SyncEngine, None]:
        """
        创建 SyncEngine 实例（异步上下文管理器）
        
        自动管理 session 生命周期：进入时创建，退出时关闭。
        
        Yields:
            装配好的 SyncEngine 实例
        """
        async with AsyncSessionLocal() as session:
            try:
                # 实例化所有依赖
                sync_task_repo = SyncTaskRepositoryImpl(session)
                stock_repo = StockRepositoryImpl(session)
                daily_repo = StockDailyRepositoryImpl(session)
                finance_repo = StockFinanceRepositoryImpl(session)
                
                quote_provider = TushareClient()
                finance_provider = TushareClient()
                
                # 装配 SyncEngine
                engine = SyncEngine(
                    sync_task_repo=sync_task_repo,
                    stock_repo=stock_repo,
                    daily_repo=daily_repo,
                    finance_repo=finance_repo,
                    quote_provider=quote_provider,
                    finance_provider=finance_provider,
                )
                
                yield engine
                
            except Exception as e:
                await session.rollback()
                raise
            finally:
                await session.close()

    @staticmethod
    @asynccontextmanager
    async def create_incremental_finance_use_case() -> AsyncGenerator[SyncIncrementalFinanceDataUseCase, None]:
        """
        创建增量财务同步 Use Case 实例（异步上下文管理器）
        
        独立创建，因为增量同步不需要 SyncEngine 的全部依赖。
        
        Yields:
            装配好的 SyncIncrementalFinanceDataUseCase 实例
        """
        async with AsyncSessionLocal() as session:
            try:
                sync_task_repo = SyncTaskRepositoryImpl(session)
                stock_repo = StockRepositoryImpl(session)
                finance_repo = StockFinanceRepositoryImpl(session)
                finance_provider = TushareClient()
                
                use_case = SyncIncrementalFinanceDataUseCase(
                    finance_repo=finance_repo,
                    stock_repo=stock_repo,
                    sync_task_repo=sync_task_repo,
                    data_provider=finance_provider,
                )
                
                yield use_case
                
            except Exception as e:
                await session.rollback()
                raise
            finally:
                await session.close()

    @staticmethod
    @asynccontextmanager
    async def create_batch_session() -> AsyncGenerator:
        """
        创建独立的批处理 session
        
        用于 SyncEngine 内部按批创建独立 session，避免长事务。
        每批完成后提交并关闭，下一批使用新 session。
        
        Yields:
            新的 AsyncSession 实例
        """
        async with AsyncSessionLocal() as session:
            try:
                yield session
            except Exception as e:
                await session.rollback()
                raise
            finally:
                await session.close()
