"""
Debate 领域枚举。

集中定义辩论方向、风险级别、论证强度等枚举，供 Domain/Application 使用。
"""
from enum import StrEnum


class DebateDirection(StrEnum):
    """辩论综合方向。"""

    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"


class RiskLevel(StrEnum):
    """风险级别。"""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ArgumentStrength(StrEnum):
    """论证强度。"""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
