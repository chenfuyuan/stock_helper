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


class ConceptRelationType(StrEnum):
    """概念间关系类型枚举。"""

    IS_UPSTREAM_OF = "IS_UPSTREAM_OF"  # 上游
    IS_DOWNSTREAM_OF = "IS_DOWNSTREAM_OF"  # 下游
    COMPETES_WITH = "COMPETES_WITH"  # 竞争
    IS_PART_OF = "IS_PART_OF"  # 组成部分
    ENABLER_FOR = "ENABLER_FOR"  # 技术驱动


class RelationSourceType(StrEnum):
    """概念关系来源类型枚举。"""

    MANUAL = "MANUAL"  # 手动创建
    LLM = "LLM"  # LLM 推荐


class RelationStatus(StrEnum):
    """概念关系状态枚举。"""

    PENDING = "PENDING"  # 待确认
    CONFIRMED = "CONFIRMED"  # 已确认
    REJECTED = "REJECTED"  # 已拒绝
