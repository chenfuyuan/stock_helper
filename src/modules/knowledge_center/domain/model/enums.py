"""
Knowledge Center 领域枚举。

定义图谱节点标签与关系类型枚举。
"""

from enum import StrEnum


class NodeLabel(StrEnum):
    """图谱节点标签枚举。"""

    STOCK = "STOCK"
    INDUSTRY = "INDUSTRY"
    AREA = "AREA"
    MARKET = "MARKET"
    EXCHANGE = "EXCHANGE"


class RelationshipType(StrEnum):
    """图谱关系类型枚举。"""

    BELONGS_TO_INDUSTRY = "BELONGS_TO_INDUSTRY"
    LOCATED_IN = "LOCATED_IN"
    TRADES_ON = "TRADES_ON"
    LISTED_ON = "LISTED_ON"
