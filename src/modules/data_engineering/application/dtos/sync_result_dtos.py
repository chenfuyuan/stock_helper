"""
数据同步 Command 的类型化返回值 DTO。

统一定义所有同步 Command 的 Result DTO，消灭 Dict[str, Any] 返回。
同时合并原先分散在多个文件中的重复定义（如 ConceptSyncResult、AkShareSyncResult）。
"""

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class DailyByDateSyncResult(BaseModel):
    """按日期同步日线数据的结果。"""

    status: str = Field(..., description="同步状态")
    count: int = Field(default=0, description="同步条数")
    message: str = Field(default="", description="结果描述")


class DailyHistorySyncResult(BaseModel):
    """历史日线全量同步单批结果。"""

    synced_stocks: int = Field(default=0, description="已同步股票数")
    total_rows: int = Field(default=0, description="已同步行数")
    message: str = Field(default="", description="结果描述")


class FinanceHistorySyncResult(BaseModel):
    """历史财务全量同步单批结果。"""

    status: str = Field(default="success", description="同步状态")
    count: int = Field(default=0, description="同步条数")
    batch_size: int = Field(default=0, description="本批处理股票数")


class IncrementalFinanceSyncResult(BaseModel):
    """增量财务同步结果。"""

    status: str = Field(default="success", description="同步状态")
    synced_count: int = Field(default=0, description="成功同步股票数")
    failed_count: int = Field(default=0, description="失败股票数")
    retry_count: int = Field(default=0, description="重试总数")
    retry_success_count: int = Field(default=0, description="重试成功数")
    target_period: str = Field(default="", description="目标报告期")
    message: str = Field(default="", description="结果描述")


class StockListSyncResult(BaseModel):
    """股票基础列表同步结果。"""

    status: str = Field(default="success", description="同步状态")
    synced_count: int = Field(default=0, description="同步条数")
    message: str = Field(default="", description="结果描述")


class ConceptSyncResult(BaseModel):
    """概念数据同步结果——合并全量与增量两处重复定义。"""

    total_concepts: int = Field(default=0, description="总概念数")
    success_concepts: int = Field(default=0, description="成功同步概念数")
    failed_concepts: int = Field(default=0, description="失败概念数")
    total_stocks: int = Field(default=0, description="总成份股映射数")
    elapsed_time: float = Field(default=0.0, description="耗时（秒）")


class AkShareSyncResult(BaseModel):
    """AkShare 市场数据同步结果——从 sync_akshare_market_data_cmd.py 迁出。"""

    trade_date: date = Field(..., description="交易日期")
    limit_up_pool_count: int = Field(default=0, description="涨停池同步条数")
    broken_board_count: int = Field(default=0, description="炸板池同步条数")
    previous_limit_up_count: int = Field(default=0, description="昨日涨停同步条数")
    dragon_tiger_count: int = Field(default=0, description="龙虎榜同步条数")
    sector_capital_flow_count: int = Field(default=0, description="板块资金流向同步条数")
    errors: list[str] = Field(default_factory=list, description="错误信息列表")


class IncrementalDailySyncResult(BaseModel):
    """增量日线同步结果（含补偿）。"""

    status: str = Field(default="success", description="同步状态")
    synced_dates: list[str] = Field(default_factory=list, description="已同步日期列表")
    total_count: int = Field(default=0, description="同步总条数")
    message: str = Field(default="", description="结果描述")
