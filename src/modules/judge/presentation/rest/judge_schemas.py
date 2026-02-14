"""
Judge REST 请求/响应 Schema。
"""

from typing import Any

from pydantic import BaseModel, Field


class JudgeVerdictRequest(BaseModel):
    """POST /api/v1/judge/verdict 请求体。"""

    symbol: str = Field(..., description="标的代码")
    debate_outcome: dict[str, Any] = Field(
        ...,
        description=(  # noqa: E501
            "辩论结果 dict，须包含 direction、confidence、bull_case、bear_case、"
            "risk_matrix、key_disagreements、conflict_resolution"
        ),
    )


class JudgeVerdictResponse(BaseModel):
    """POST /api/v1/judge/verdict 响应体（VerdictDTO 的 JSON 序列化）。"""

    symbol: str
    action: str = Field(..., description="BUY | SELL | HOLD")
    position_percent: float = Field(..., ge=0.0, le=1.0)
    confidence: float = Field(..., ge=0.0, le=1.0)
    entry_strategy: str
    stop_loss: str
    take_profit: str
    time_horizon: str
    risk_warnings: list[str] = Field(default_factory=list)
    reasoning: str
