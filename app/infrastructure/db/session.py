from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

# 创建异步数据库引擎
engine = create_async_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    echo=False,  # 设置为 True 可打印 SQL 语句
    future=True,
    pool_pre_ping=True, # 每次从连接池获取连接前预先检测连接是否有效
)

# 创建异步会话工厂
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False, # 提交后不立即使对象过期，便于异步操作
    autocommit=False,
    autoflush=False,
)

async def get_db_session() -> AsyncSession:
    """
    获取数据库会话的依赖注入函数
    FastAPI Depends 使用此生成器管理会话生命周期
    """
    async with AsyncSessionLocal() as session:
        yield session
