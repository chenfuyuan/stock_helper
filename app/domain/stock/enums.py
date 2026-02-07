from enum import Enum

class ListStatus(str, Enum):
    """上市状态"""
    LISTED = "L"   # 上市
    DELISTED = "D" # 退市
    PAUSED = "P"   # 暂停上市

class IsHs(str, Enum):
    """沪深港通标的"""
    NO = "N"      # 否
    HK = "H"      # 沪股通
    SZ = "S"      # 深股通

class MarketType(str, Enum):
    """市场类型"""
    MAIN = "主板"
    STARTUP = "创业板"
    STAR = "科创板"
    CDR = "CDR"
    BSE = "北交所"
    
class ExchangeType(str, Enum):
    """交易所"""
    SSE = "SSE"   # 上交所
    SZSE = "SZSE" # 深交所
    BSE = "BSE"   # 北交所
