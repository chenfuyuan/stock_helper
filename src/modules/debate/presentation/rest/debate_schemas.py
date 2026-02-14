"""
Debate REST 请求/响应 Schema。
"""

from typing import Any

from pydantic import BaseModel, Field


class DebateRunRequest(BaseModel):
    """POST /api/v1/debate/run 请求体。"""

    symbol: str = Field(..., description="标的代码")
    expert_results: dict[str, dict[str, Any]] = Field(
        ...,
        description="按专家名分组的研究结果，每个 value 为该专家的结果 dict",
    )


class DebateRunResponse(BaseModel):
    """POST /api/v1/debate/run 响应体（DebateOutcomeDTO 的 JSON 序列化）。"""

    symbol: str
    direction: str = Field(..., description="BULLISH | BEARISH | NEUTRAL")
    confidence: float = Field(..., ge=0.0, le=1.0)
    bull_case: dict[str, Any] = Field(..., description="多头论点摘要")
    bear_case: dict[str, Any] = Field(..., description="空头论点摘要")
    risk_matrix: list[dict[str, Any]] = Field(..., description="风险矩阵")
    key_disagreements: list[str] = Field(..., description="核心分歧点")
    conflict_resolution: str = Field(..., description="冲突消解结论")
