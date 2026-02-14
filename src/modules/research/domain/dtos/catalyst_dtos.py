from typing import List, Literal

from pydantic import BaseModel

from src.modules.research.domain.dtos.catalyst_context import (
    CatalystContextDTO,
)


class CatalystEvent(BaseModel):
    """
    单一催化事件 (Value Object)
    """

    event: str  # 事件描述
    expected_impact: str  # 预期对股价/基本面的影响
    timeframe: str  # 时间线：近期/中期/远期
    probability: str  # 触发概率：高/中/低


class CatalystDimensionAnalysis(BaseModel):
    """
    单一维度的催化剂分析结果
    """

    dimension: str
    assessment: str
    score: int  # 0-100
    key_findings: List[str]


class CatalystDetectiveResultDTO(BaseModel):
    """
    催化剂侦探分析结果 (Output DTO)
    """

    catalyst_assessment: Literal[
        "Positive (正面催化)", "Neutral (中性)", "Negative (负面催化)"
    ]
    confidence_score: float  # 0.0 - 1.0
    catalyst_summary: str
    dimension_analyses: List[CatalystDimensionAnalysis]
    positive_catalysts: List[CatalystEvent]
    negative_catalysts: List[CatalystEvent]
    information_sources: List[str]
    narrative_report: str = (
        ""  # 面向人类的中文叙述性报告：核心结论、论据、风险、置信度
    )


class CatalystDetectiveAgentResult(BaseModel):
    """
    Agent 调用的完整返回结果，包含解析后的 DTO 和原始 LLM 输出
    """

    result: CatalystDetectiveResultDTO
    raw_llm_output: str
    user_prompt: str
    catalyst_context: CatalystContextDTO
