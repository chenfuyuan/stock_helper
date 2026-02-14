"""
技术分析师输出契约 DTO。
与 Spec 输出契约一致：signal、confidence、summary_reasoning、key_technical_levels、risk_warning。
"""

from typing import Literal

from pydantic import BaseModel, Field

TechnicalSignal = Literal["BULLISH", "BEARISH", "NEUTRAL"]


class KeyTechnicalLevelsDTO(BaseModel):
    """关键价位：支撑与阻力。"""

    support: float = Field(..., description="关键支撑位")
    resistance: float = Field(..., description="关键阻力位")


class TechnicalAnalysisResultDTO(BaseModel):
    """
    技术分析师产出 DTO。
    用于 LLM 输出解析与 Application 层返回，不暴露内部领域模型。
    """

    signal: TechnicalSignal = Field(..., description="BULLISH/BEARISH/NEUTRAL")
    confidence: float = Field(..., ge=0.0, le=1.0, description="置信度 0~1")
    summary_reasoning: str = Field(..., description="简练分析逻辑，须引用输入指标")
    key_technical_levels: KeyTechnicalLevelsDTO = Field(..., description="关键支撑/阻力")
    risk_warning: str = Field(..., description="观点被证伪时的关键点位描述")
    narrative_report: str = Field(
        "",
        description="面向人类的中文叙述性报告：核心结论、论据、风险、置信度",
    )


class TechnicalAnalysisAgentResult(BaseModel):
    """
    Agent 层返回的完整结果：解析后的 DTO + 大模型原始输出 + 送入大模型的 user prompt。
    供 Application/API 层组装响应体时填入 input、output 等字段（代码侧塞入，非大模型拼接）。
    """

    result: TechnicalAnalysisResultDTO = Field(..., description="解析后的技术分析结果")
    raw_llm_output: str = Field(..., description="大模型原始返回字符串")
    user_prompt: str = Field(..., description="送入大模型的 user prompt（填充后的模板）")
