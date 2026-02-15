"""
概念关系分析器 DTO。

用于 LLM 分析输入输出的数据传输对象。
"""

from pydantic import BaseModel, Field


class ConceptForAnalysis(BaseModel):
    """
    待分析概念 DTO。
    
    用于传递给 LLM 进行产业链关系分析的概念信息。
    """

    code: str = Field(description="概念代码")
    name: str = Field(description="概念名称")


class SuggestedRelation(BaseModel):
    """
    LLM 推荐关系 DTO。
    
    表示 LLM 分析后推荐的概念间关系及其推理依据。
    """

    source_concept_code: str = Field(description="源概念代码")
    target_concept_code: str = Field(description="目标概念代码")
    relation_type: str = Field(description="关系类型（如 IS_UPSTREAM_OF）")
    confidence: float = Field(description="置信度（0.0~1.0）")
    reasoning: str = Field(description="推理依据（LLM 给出的解释）")
