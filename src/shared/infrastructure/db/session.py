from typing import AsyncGenerator

from loguru import logger
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    create_async_engine,
)
from sqlalchemy.orm import sessionmaker

from src.shared.config import settings

# 创建异步数据库引擎
engine: AsyncEngine = create_async_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    echo=False,  # 设置为 True 可打印 SQL 语句
    future=True,
    pool_pre_ping=True,  # 每次从连接池获取连接前预先检测连接是否有效
)

# 创建异步会话工厂
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,  # 提交后不立即使对象过期，便于异步操作
    autocommit=False,
    autoflush=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
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
            # 区分处理业务异常/客户端异常与系统异常
            from fastapi import HTTPException

            from src.shared.domain.exceptions import (
                BadRequestException,
                ForbiddenException,
                NotFoundException,
                UnauthorizedException,
            )

            is_client_error = False

            # 检查是否为 FastAPI HTTPException 且状态码为 4xx
            if isinstance(e, HTTPException) and 400 <= e.status_code < 500:
                is_client_error = True
            # 检查是否为自定义业务异常 (通常映射为 4xx)
            elif isinstance(
                e,
                (
                    BadRequestException,
                    NotFoundException,
                    UnauthorizedException,
                    ForbiddenException,
                ),
            ):
                is_client_error = True

            if is_client_error:
                # 客户端错误/业务校验不通过，通过日志记录 INFO/WARNING，不回滚 (Read操作通常无需回滚，Write操作自动回滚)
                # 注意：SQLAlchemy async session 在关闭时会自动回滚未提交的事务
                logger.warning(f"请求处理异常 (Client Error): {str(e)}")
            else:
                # 系统异常，记录 ERROR 并显式回滚
                logger.error(f"数据库会话运行异常: {str(e)}")
                await session.rollback()
            raise
        finally:
            await session.close()
