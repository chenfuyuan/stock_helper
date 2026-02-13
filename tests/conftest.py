import asyncio
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from src.shared.config import settings
from src.shared.infrastructure.db.base import Base

# Use an in-memory SQLite for testing or a separate Postgres DB
# For this skeleton, we assume the environment provides a test DB URL
# or we mock it. But integration tests usually need a real DB.
# We will use the settings one, assuming CI sets up a test DB.

import pytest
import asyncio

# 移除所有自定义 event_loop 相关 fixture
# 让 pytest-asyncio 自动管理，通过 pytest.ini 或配置钩子指定 loop scope

@pytest.fixture(scope="session")
async def db_engine():
    # 注意：这里使用开发数据库，为了避免清空数据，移除了 drop_all
    # 建议在生产环境测试中使用独立的测试数据库
    engine = create_async_engine(settings.SQLALCHEMY_DATABASE_URI, pool_pre_ping=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    # 移除 drop_all 以保护开发数据
    # async with engine.begin() as conn:
    #     await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest.fixture
async def db_session(db_engine):
    # 使用事务回滚模式，测试数据不会提交到数据库
    connection = await db_engine.connect()
    transaction = await connection.begin()
    
    async_session = sessionmaker(
        bind=connection,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with async_session() as session:
        yield session
        
    await transaction.rollback()
    await connection.close()

@pytest.fixture
async def client(db_session):
    from src.main import app
    async with AsyncClient(app=app, base_url="http://test") as c:
        yield c
