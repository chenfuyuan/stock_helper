"""
估值建模师输出契约 DTO。
与 Spec 输出契约一致：valuation_verdict（英文枚举）、confidence_score、estimated_intrinsic_value_range、
key_evidence、risk_factors、reasoning_summary。中文仅用于展示层。
"""

from typing import Literal

from pydantic import BaseModel, Field

ValuationVerdict = Literal["Undervalued", "Fair", "Overvalued"]

# 展示层用：英文 verdict → 中文标签（API 返回英文，前端/报告按需映射）
VERDICT_DISPLAY_LABELS: dict[str, str] = {
    "Undervalued": "低估",
    "Fair": "合理",
    "Overvalued": "高估",
}


class IntrinsicValueRangeDTO(BaseModel):
    """
    内在价值区间 DTO。
    lower_bound 和 upper_bound 为描述性字符串，包含推导依据（如"基于 Graham 模型推导的 18.5 元"）。
    """

    lower_bound: str = Field(..., description="保守模型推导的价格下界（含推导依据）")
    upper_bound: str = Field(..., description="乐观模型推导的价格上界（含推导依据）")


class ValuationResultDTO(BaseModel):
    """
    估值建模师产出 DTO。
    用于 LLM 输出解析与 Application 层返回，不暴露内部领域模型。
    """

    valuation_verdict: ValuationVerdict = Field(
        ...,
        description="估值判断枚举：Undervalued / Fair / Overvalued，展示时可用 VERDICT_DISPLAY_LABELS 映射为中文",
    )
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="置信度 0~1，基于证据一致性")
    estimated_intrinsic_value_range: IntrinsicValueRangeDTO = Field(
        ..., description="估值模型推导的内在价值区间（含推导依据）"
    )
    key_evidence: list[str] = Field(
        ..., min_length=1, description="证据列表，须引用输入数据中的具体数值"
    )
    risk_factors: list[str] = Field(..., min_length=1, description="风险列表")
    reasoning_summary: str = Field(..., description="专业精炼总结，须明确指出是机会还是陷阱")
    narrative_report: str = Field(
        "",
        description="面向人类的中文叙述性报告：核心结论、论据、风险、置信度",
    )


class ValuationModelAgentResult(BaseModel):
    """
    Agent 层返回的完整结果：解析后的 DTO + 大模型原始输出 + 送入大模型的 user prompt。
    供 Application/API 层组装响应体时填入 input、output 等字段（代码侧塞入，非大模型拼接）。
    """

    result: ValuationResultDTO = Field(..., description="解析后的估值建模结果")
    raw_llm_output: str = Field(..., description="大模型原始返回字符串")
    user_prompt: str = Field(..., description="送入大模型的 user prompt（填充后的模板）")
