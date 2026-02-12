"""
数据工程模块专属配置。

将 Tushare、同步相关配置从 shared/config 下沉到本模块，实现配置按 Bounded Context 隔离。
"""

from pydantic_settings import BaseSettings


class DataEngineeringConfig(BaseSettings):
    """数据工程模块配置：Tushare API 与同步引擎参数。"""

    TUSHARE_TOKEN: str = "your_tushare_token_here"
    TUSHARE_MIN_INTERVAL: float = 0.35
    SYNC_DAILY_HISTORY_BATCH_SIZE: int = 50
    SYNC_FINANCE_HISTORY_BATCH_SIZE: int = 100
    SYNC_FINANCE_HISTORY_START_DATE: str = "20200101"
    SYNC_INCREMENTAL_MISSING_LIMIT: int = 300
    SYNC_FAILURE_MAX_RETRIES: int = 3

    class Config:
        case_sensitive = True
        env_file = ".env"
        extra = "ignore"


de_config = DataEngineeringConfig()
