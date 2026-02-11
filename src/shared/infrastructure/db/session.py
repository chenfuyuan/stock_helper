from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from loguru import logger

from src.shared.config import settings

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
    获取数据库会话的依赖注入函数 (Dependency)
    FastAPI Depends 使用此生成器管理会话生命周期。
    
    Yields:
        AsyncSession: 异步数据库会话
    
    Note:
        使用 context manager 确保即使发生异常也能正确关闭会话。
        如果发生异常，会执行 rollback 并记录错误日志。
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"数据库会话运行异常: {str(e)}")
            await session.rollback()
            raise
        finally:
            await session.close()
