"""
Judge 领域枚举。

定义裁决输出中的操作方向等值对象。
"""
from enum import Enum


class ActionDirection(str, Enum):
    """操作方向：买入、卖出或观望。"""

    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
