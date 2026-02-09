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
