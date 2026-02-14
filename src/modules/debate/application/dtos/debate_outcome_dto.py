"""
辩论结果 DTO（Application 层对外暴露）。

仅包含基本类型与 DTO，不引用 Domain 实体。
"""

from pydantic import BaseModel

from src.modules.debate.domain.dtos.risk_matrix import RiskItemDTO


class BullCaseDTO(BaseModel):
    """多头论点摘要。"""

    core_thesis: str
    supporting_arguments: list[str]
    acknowledged_risks: list[str]


class BearCaseDTO(BaseModel):
    """空头论点摘要。"""

    core_thesis: str
    supporting_arguments: list[str]
    acknowledged_strengths: list[str]


class DebateOutcomeDTO(BaseModel):
    """辩论产出 DTO，对外暴露。"""

    symbol: str
    direction: str  # "BULLISH" | "BEARISH" | "NEUTRAL"
    confidence: float  # 0.0 - 1.0
    bull_case: BullCaseDTO
    bear_case: BearCaseDTO
    risk_matrix: list[RiskItemDTO]
    key_disagreements: list[str]
    conflict_resolution: str
