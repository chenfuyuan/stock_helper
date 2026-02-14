"""
宏观情报员输出型 DTO。

定义宏观分析的结果数据结构，包含单维度分析与完整宏观评估。
"""

from typing import List, Literal

from pydantic import BaseModel, Field, field_validator


class MacroDimensionAnalysis(BaseModel):
    """
    单个宏观维度的分析结果。

    对应四个宏观维度（货币与流动性、产业政策与监管、宏观经济周期、行业景气与资金流向）
    中的一个，包含该维度的评估文本、评分和关键发现。
    """

    dimension: str = Field(..., description="维度名称（如'货币与流动性环境'）")
    assessment: str = Field(..., description="该维度的评估文本")
    score: int = Field(..., ge=0, le=100, description="该维度的评分（0-100）")
    key_findings: List[str] = Field(..., description="该维度的关键发现列表")


class MacroIntelligenceResultDTO(BaseModel):
    """
    宏观情报员的完整分析结果。

    包含宏观环境的三值判定（有利/中性/不利）、置信度、综合摘要、
    四个维度的详细分析、机会列表、风险列表以及信息来源。

    该 DTO 对应 LLM 返回的 JSON 结构，需要通过 output_parser 从 LLM 输出中解析。
    """

    macro_environment: Literal["Favorable (有利)", "Neutral (中性)", "Unfavorable (不利)"] = Field(
        ..., description="宏观环境综合判定（三值之一）"
    )
    confidence_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="置信度评分（0.0-1.0），基于证据充分性与一致性",
    )
    macro_summary: str = Field(..., description="宏观环境综合判断，须引用搜索证据")
    dimension_analyses: List[MacroDimensionAnalysis] = Field(
        ..., description="四个维度的详细分析（货币、政策、经济、行业）"
    )
    key_opportunities: List[str] = Field(..., description="宏观层面的机会列表")
    key_risks: List[str] = Field(..., description="宏观层面的风险列表")
    information_sources: List[str] = Field(..., description="引用的信息来源 URL 列表，用于溯源审计")
    narrative_report: str = Field(
        "",
        description="面向人类的中文叙述性报告：核心结论、论据、风险、置信度",
    )

    @field_validator("dimension_analyses")
    @classmethod
    def validate_dimension_count(
        cls, v: List[MacroDimensionAnalysis]
    ) -> List[MacroDimensionAnalysis]:
        """
        校验维度分析数量：必须包含 4 个维度的分析。

        Args:
            v: 维度分析列表

        Returns:
            原列表（校验通过时）

        Raises:
            ValueError: 维度数量不为 4 时
        """
        if len(v) != 4:
            raise ValueError(f"dimension_analyses 必须包含 4 个维度的分析，实际包含 {len(v)} 个")
        return v

    @field_validator("key_opportunities", "key_risks", "information_sources")
    @classmethod
    def validate_non_empty_list(cls, v: List[str]) -> List[str]:
        """
        校验列表非空：key_opportunities、key_risks、information_sources 必须至少包含一个元素。

        Args:
            v: 待校验的列表

        Returns:
            原列表（校验通过时）

        Raises:
            ValueError: 列表为空时
        """
        if not v:
            raise ValueError("该字段必须至少包含一个元素")
        return v


class MacroIntelligenceAgentResult(BaseModel):
    """
    宏观情报员 Agent 的完整返回结果。

    除了解析后的宏观分析结果外，还包含原始 LLM 输出和发送的 user prompt，
    便于调试、审计和问题追溯。
    """

    result: MacroIntelligenceResultDTO = Field(..., description="解析后的宏观分析结果")
    raw_llm_output: str = Field(..., description="LLM 原始返回字符串（未解析前）")
    user_prompt: str = Field(..., description="发送给 LLM 的 user prompt（已填充占位符）")
