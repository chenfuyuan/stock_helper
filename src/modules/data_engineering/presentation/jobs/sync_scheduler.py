"""定时任务 Job 函数定义——所有 Job 精简为调用 DataSyncApplicationService。"""

from src.modules.data_engineering.application.services.data_sync_application_service import (
    DataSyncApplicationService,
)


async def sync_history_daily_data_job():
    """定时任务：同步股票历史日线数据（全量历史）。"""
    service = DataSyncApplicationService()
    await service.run_daily_history_sync()


async def sync_daily_data_job(target_date: str | None = None):
    """
    定时任务：每日增量同步日线数据。
    
    Args:
        target_date: 目标日期 (YYYYMMDD)，默认为当天
    """
    service = DataSyncApplicationService()
    await service.run_daily_incremental_sync(target_date)


async def sync_finance_history_job():
    """定时任务：同步历史财务数据（全量历史）。"""
    service = DataSyncApplicationService()
    await service.run_finance_history_sync()


async def sync_incremental_finance_job(target_date: str | None = None):
    """
    定时任务：增量同步财务数据。
    
    Args:
        target_date: 目标日期 (YYYYMMDD)，默认为当天
    """
    service = DataSyncApplicationService()
    await service.run_incremental_finance_sync(target_date)


async def sync_concept_data_job():
    """定时任务：同步概念数据（akshare → PostgreSQL）。"""
    service = DataSyncApplicationService()
    await service.run_concept_sync()


async def sync_stock_basic_job():
    """定时任务：同步股票基础信息（TuShare → PostgreSQL）。"""
    service = DataSyncApplicationService()
    await service.run_stock_basic_sync()
