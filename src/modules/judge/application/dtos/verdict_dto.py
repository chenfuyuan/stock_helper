"""
裁决输出 DTO（Application 层对外暴露）。

包含 symbol（由 JudgeService 从 JudgeInput 注入）及裁决全部字段。
"""

from pydantic import BaseModel, Field


class VerdictDTO(BaseModel):
    """裁决结果，供 REST 与 Coordinator 使用。"""

    symbol: str = Field(..., description="标的代码")
    action: str = Field(..., description="操作方向：BUY | SELL | HOLD")
    position_percent: float = Field(
        ..., ge=0.0, le=1.0, description="建议仓位比例 0.0–1.0"
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="裁决置信度 0.0–1.0"
    )
    entry_strategy: str = Field(..., description="入场策略描述")
    stop_loss: str = Field(..., description="止损策略")
    take_profit: str = Field(..., description="止盈策略")
    time_horizon: str = Field(..., description="持有周期建议")
    risk_warnings: list[str] = Field(
        default_factory=list, description="关键风控约束"
    )
    reasoning: str = Field("", description="裁决理由摘要；未提供时为空字符串")
