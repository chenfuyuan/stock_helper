"""
Knowledge Center 领域枚举。

定义图谱节点标签与关系类型枚举。
"""

import sys
from enum import Enum

# Python 3.10 兼容性处理
if sys.version_info >= (3, 11):
    from enum import StrEnum
else:
    class StrEnum(str, Enum):
        """Python 3.10 兼容的 StrEnum 实现"""
        pass


class NodeLabel(StrEnum):
    """图谱节点标签枚举。"""

    STOCK = "STOCK"
    INDUSTRY = "INDUSTRY"
    AREA = "AREA"
    MARKET = "MARKET"
    EXCHANGE = "EXCHANGE"
    CONCEPT = "CONCEPT"


class RelationshipType(StrEnum):
    """图谱关系类型枚举。"""

    BELONGS_TO_INDUSTRY = "BELONGS_TO_INDUSTRY"
    LOCATED_IN = "LOCATED_IN"
    TRADES_ON = "TRADES_ON"
    LISTED_ON = "LISTED_ON"
    BELONGS_TO_CONCEPT = "BELONGS_TO_CONCEPT"
