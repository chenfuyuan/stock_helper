from enum import Enum


class ListStatus(str, Enum):
    LISTED = "L"
    DELISTED = "D"
    PAUSED = "P"


class IsHs(str, Enum):
    NO = "N"
    HK = "H"
    SZ = "S"


class ExchangeType(str, Enum):
    SSE = "SSE"
    SZSE = "SZSE"
    BSE = "BSE"


class MarketType(str, Enum):
    MAIN = "主板"
    SME = "中小板"
    GEM = "创业板"
    KCB = "科创板"
    CDR = "CDR"
    BSE = "北交所"


class SyncJobType(str, Enum):
    """同步任务类型枚举"""

    DAILY_HISTORY = "DAILY_HISTORY"  # 历史日线全量同步
    FINANCE_HISTORY = "FINANCE_HISTORY"  # 历史财务全量同步
    DAILY_INCREMENTAL = "DAILY_INCREMENTAL"  # 日线增量同步
    FINANCE_INCREMENTAL = "FINANCE_INCREMENTAL"  # 财务增量同步
    AKSHARE_MARKET_DATA = "AKSHARE_MARKET_DATA"  # AkShare 市场情绪与资金数据同步


class SyncTaskStatus(str, Enum):
    """同步任务状态枚举"""

    PENDING = "PENDING"  # 待开始
    RUNNING = "RUNNING"  # 运行中
    COMPLETED = "COMPLETED"  # 已完成
    FAILED = "FAILED"  # 失败
    PAUSED = "PAUSED"  # 已暂停
