"""Data Engineering 模块任务注册表

导出所有数据同步 Job 的映射，供 Foundation 调度器使用。
按照 Application 层归属原则，注册表从 Presentation 层提升到此处。
"""

from typing import Dict, Callable

from src.modules.data_engineering.presentation.jobs.sync_scheduler import (
    sync_daily_data_job,
    sync_finance_history_job,
    sync_history_daily_data_job,
    sync_incremental_finance_job,
    sync_concept_data_job,
    sync_stock_basic_job,
)
from src.modules.data_engineering.presentation.jobs.akshare_market_data_jobs import (
    sync_akshare_market_data_job,
)


def get_job_registry() -> Dict[str, Callable]:
    """获取 Data Engineering 模块的任务注册表
    
    Returns:
        任务 ID 到任务函数的映射字典
    """
    return {
        "sync_daily_history": sync_history_daily_data_job,
        "sync_daily_by_date": sync_daily_data_job,
        "sync_history_finance": sync_finance_history_job,
        "sync_incremental_finance": sync_incremental_finance_job,
        "sync_concept_data": sync_concept_data_job,
        "sync_stock_basic": sync_stock_basic_job,
        "sync_akshare_market_data": sync_akshare_market_data_job,
    }
