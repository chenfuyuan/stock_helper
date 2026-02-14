"""
Resolution 裁决结果 DTO。

由 Resolution Agent 产出，包含综合方向、置信度、多空摘要、风险矩阵与冲突消解结论。
"""

from pydantic import BaseModel

from src.modules.debate.domain.dtos.risk_matrix import RiskItemDTO


class ResolutionResult(BaseModel):
    """冲突消解与最终裁决结果。"""

    direction: str  # "BULLISH" | "BEARISH" | "NEUTRAL"
    confidence: float  # 0.0 - 1.0
    bull_case_summary: str  # 多头论证摘要
    bear_case_summary: str  # 空头论证摘要
    risk_matrix: list[RiskItemDTO]  # 风险矩阵
    key_disagreements: list[str]  # 核心分歧点
    conflict_resolution: str  # 冲突消解结论
    narrative_report: str = ""  # 面向人类的中文叙述性报告：核心结论、论据、风险、置信度
