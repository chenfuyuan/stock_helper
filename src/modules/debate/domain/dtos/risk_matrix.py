"""
风险矩阵 DTO。

用于 Resolution 结果与对外 DebateOutcome 中的 risk_matrix 字段。
"""

from pydantic import BaseModel


class RiskItemDTO(BaseModel):
    """单条风险项。"""

    risk: str  # 风险描述
    probability: str  # 发生概率描述
    impact: str  # 影响程度描述
    mitigation: str  # 缓解措施
