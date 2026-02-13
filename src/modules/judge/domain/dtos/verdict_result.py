"""
裁决结果 DTO（Agent 返回的领域结构）。

不含 symbol，symbol 由 JudgeService 从 JudgeInput 注入到对外 VerdictDTO。
"""
from pydantic import BaseModel, Field


class VerdictResult(BaseModel):
    """Agent 返回的原始裁决结构。"""

    action: str = Field(..., description="操作方向：BUY | SELL | HOLD")
    position_percent: float = Field(..., ge=0.0, le=1.0, description="建议仓位比例 0.0–1.0")
    confidence: float = Field(..., ge=0.0, le=1.0, description="裁决置信度 0.0–1.0")
    entry_strategy: str = Field(..., description="入场策略描述")
    stop_loss: str = Field(..., description="止损策略")
    take_profit: str = Field(..., description="止盈策略")
    time_horizon: str = Field(..., description="持有周期建议")
    risk_warnings: list[str] = Field(default_factory=list, description="关键风控约束")
    reasoning: str = Field("", description="裁决理由摘要；LLM 未返回时使用空字符串")
