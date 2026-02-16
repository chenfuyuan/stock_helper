"""定时任务 Job 函数定义——所有 Job 精简为调用专门的服务。"""

from src.modules.data_engineering.application.services.daily_sync_service import (
    DailySyncService,
)
from src.modules.data_engineering.application.services.finance_sync_service import (
    FinanceSyncService,
)
from src.modules.data_engineering.application.services.basic_data_sync_service import (
    BasicDataSyncService,
)


async def sync_history_daily_data_job():
    """定时任务：同步股票历史日线数据（全量历史）。"""
    service = DailySyncService()
    await service.run_history_sync()


async def sync_daily_data_job(target_date: str | None = None):
    """
    定时任务：每日增量同步日线数据。
    
    Args:
        target_date: 目标日期 (YYYYMMDD)，默认为当天
    """
    service = DailySyncService()
    await service.run_incremental_sync(target_date)


async def sync_finance_history_job():
    """定时任务：同步历史财务数据（全量历史）。"""
    service = FinanceSyncService()
    await service.run_history_sync()


async def sync_incremental_finance_job(target_date: str | None = None):
    """
    定时任务：增量同步财务数据。
    
    Args:
        target_date: 目标日期 (YYYYMMDD)，默认为当天
    """
    service = FinanceSyncService()
    await service.run_incremental_sync(target_date)


async def sync_concept_data_job():
    """定时任务：同步概念数据（akshare → PostgreSQL）。"""
    service = BasicDataSyncService()
    await service.run_concept_sync()


async def sync_stock_basic_job():
    """定时任务：同步股票基础信息（TuShare → PostgreSQL）。"""
    service = BasicDataSyncService()
    await service.run_stock_basic_sync()
