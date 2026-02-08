import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context
from app.core.config import settings
from app.infrastructure.db.base import Base
from app.infrastructure.db.models.stock_info import StockModel  # noqa
from app.infrastructure.db.models.stock_daily import StockDailyModel  # noqa
from app.infrastructure.db.models.stock_finance import StockFinanceModel  # noqa

# Alembic 配置对象，提供对 .ini 文件的访问
config = context.config

# 配置 Python 日志
# 这行代码基本上是设置日志记录器
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 在此处添加模型的 MetaData 对象
# 用于 'autogenerate' 自动生成迁移脚本支持
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = Base.metadata

# 其他配置值，如果 env.py 需要，可以从 config 获取
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

def get_url():
    """从应用配置中获取数据库连接 URL"""
    return settings.SQLALCHEMY_DATABASE_URI

def run_migrations_offline() -> None:
    """
    以 '离线' 模式运行迁移。

    这种模式下，仅配置 URL 而不创建 Engine。
    通过跳过 Engine 创建，甚至不需要 DBAPI 可用。

    在此处的 context.execute() 调用会将给定的字符串输出到脚本输出。
    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """执行迁移的具体逻辑"""
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """
    以 '在线' 模式运行迁移。

    在这种场景下，我们需要创建一个 Engine 并将连接关联到 context。
    """
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = get_url()
    
    # 创建异步 Engine
    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        # 在同步上下文中运行迁移
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
