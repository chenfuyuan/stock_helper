"""
Market Insight 领域模型枚举定义
"""

from enum import Enum


class LimitType(str, Enum):
    """涨停类型枚举"""
    
    MAIN_BOARD = "MAIN_BOARD"
    GEM = "GEM"
    STAR = "STAR"
    BSE = "BSE"
    ST = "ST"
