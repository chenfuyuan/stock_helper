"""AkShare 市场数据同步任务——所有 Job 精简为调用 DataSyncApplicationService。"""

from src.modules.data_engineering.application.services.data_sync_application_service import (
    DataSyncApplicationService,
)


async def sync_akshare_market_data_job(target_date: str | None = None):
    """
    定时任务：同步 AkShare 市场数据（涨停池、炸板池、昨日涨停、龙虎榜、板块资金流向）。
    
    Args:
        target_date: 目标日期 (YYYYMMDD)，默认为当天
    """
    service = DataSyncApplicationService()
    await service.run_akshare_market_data_sync(target_date)
