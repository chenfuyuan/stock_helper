"""
裁决输入 DTO。

由调用方（如 JudgeGatewayAdapter）从辩论结果转换而来，仅包含结论级字段。
"""

from pydantic import BaseModel, Field


class JudgeInput(BaseModel):
    """裁决所需输入，归一化后的结论级字段。"""

    symbol: str = Field(..., description="标的代码")
    direction: str = Field(
        ...,
        description="辩论综合方向：BULLISH | BEARISH | NEUTRAL",
    )
    confidence: float = Field(..., ge=0.0, le=1.0, description="辩论综合置信度 0.0–1.0")
    bull_thesis: str = Field(..., description="多头核心论点")
    bear_thesis: str = Field(..., description="空头核心论点")
    risk_factors: list[str] = Field(default_factory=list, description="风险因子摘要")
    key_disagreements: list[str] = Field(default_factory=list, description="核心分歧点")
    conflict_resolution: str = Field(..., description="冲突消解结论")
