"""
辩论输入 DTO。

从 Coordinator/Research 结果转换而来，仅包含辩论所需的归一化字段（symbol + 各专家摘要）。
"""

from pydantic import BaseModel


class ExpertSummary(BaseModel):
    """
    单专家摘要（归一化后的四个语义字段）。

    由调用方（如 DebateGatewayAdapter）从各专家不同的原始字段名映射而来，
    不包含 input、output、indicators 等调试/大体积字段。
    """

    signal: str  # 专家信号，如 "BULLISH"、"BEARISH"
    confidence: float  # 置信度
    reasoning: str  # 分析逻辑摘要
    risk_warning: str  # 风险警示


class DebateInput(BaseModel):
    """辩论输入：标的代码 + 按专家名分组的专家摘要。"""

    symbol: str
    expert_summaries: dict[
        str, ExpertSummary
    ]  # key 为专家类型名，如 "technical_analyst"
