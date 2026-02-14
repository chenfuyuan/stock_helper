"""
财务审计员输出契约 DTO。
与 Spec 输出契约一致：financial_score、signal、confidence、summary_reasoning、
dimension_analyses、key_risks、risk_warning。
"""

from typing import Literal

from pydantic import BaseModel, Field

FinancialSignal = Literal["STRONG_BULLISH", "BULLISH", "NEUTRAL", "BEARISH", "STRONG_BEARISH"]


class DimensionAnalysisDTO(BaseModel):
    """5D 审计模型中单维度的分析结果。"""

    dimension: str = Field(..., description="维度名称")
    score: float = Field(..., description="该维度评分")
    assessment: str = Field(..., description="简评")
    key_findings: list[str] = Field(default_factory=list, description="关键发现列表")


class FinancialAuditResultDTO(BaseModel):
    """
    财务审计员产出 DTO。
    用于 LLM 输出解析与 Application 层返回，不暴露内部领域模型。
    """

    financial_score: int = Field(..., ge=0, le=100, description="整体财务健康评分 0–100")
    signal: FinancialSignal = Field(
        ...,
        description="STRONG_BULLISH/BULLISH/NEUTRAL/BEARISH/STRONG_BEARISH",
    )
    confidence: float = Field(..., ge=0.0, le=1.0, description="置信度 0~1")
    summary_reasoning: str = Field(..., description="审计逻辑摘要，须引用输入中的财务指标读数")
    dimension_analyses: list[DimensionAnalysisDTO] = Field(
        ...,
        description="5 个维度的分析结果",
        min_length=1,
    )
    key_risks: list[str] = Field(default_factory=list, description="主要风险标记")
    risk_warning: str = Field(..., description="评估被证伪时的关键条件描述")
    narrative_report: str = Field(
        "",
        description="面向人类的中文叙述性报告：核心结论、论据、风险、置信度",
    )


class FinancialAuditAgentResult(BaseModel):
    """
    Agent 层返回的完整结果：解析后的 DTO + 大模型原始输出 + 送入大模型的 user prompt。
    供 Application/API 层组装响应体时填入 input、output 等字段（代码侧塞入，非大模型拼接）。
    """

    result: FinancialAuditResultDTO = Field(..., description="解析后的财务审计结果")
    raw_llm_output: str = Field(..., description="大模型原始返回字符串")
    user_prompt: str = Field(..., description="送入大模型的 user prompt（填充后的模板）")
