"""
概念关系分析相关的 DTO。

用于 LLM 分析结果的解析和验证。
"""

from typing import List

from pydantic import BaseModel, Field, ValidationError, root_validator


class SuggestedRelationDTO(BaseModel):
    """LLM 推荐的单条关系 DTO。"""
    
    source: str = Field(description="源概念代码")
    target: str = Field(description="目标概念代码")
    type: str = Field(description="关系类型")
    confidence: float = Field(description="置信度", ge=0.0, le=1.0)
    reasoning: str = Field(description="推理说明")


class ConceptRelationsAnalysisResultDTO(BaseModel):
    """概念关系分析结果 DTO。"""
    
    relations: List[SuggestedRelationDTO] = Field(description="推荐关系列表")
    
    @root_validator(pre=True)
    def validate_relations(cls, values):
        """验证关系列表。"""
        relations = values.get("relations", [])
        if not isinstance(relations, list):
            raise ValueError("relations 必须是列表")
        return values


# 归一化钩子：将 relations 字段从 dict 转换为 DTO 列表
def normalize_relations(data: dict) -> dict:
    """归一化钩子：将 relations 字段从 dict 列表转换为 DTO 列表。"""
    if "relations" in data and isinstance(data["relations"], list):
        try:
            # 验证每个关系对象
            normalized_relations = []
            for rel in data["relations"]:
                if isinstance(rel, dict):
                    normalized_relations.append(rel)
                else:
                    raise ValueError(f"关系对象必须是字典，实际类型: {type(rel)}")
            data["relations"] = normalized_relations
        except Exception as e:
            raise ValueError(f"关系列表归一化失败: {str(e)}")
    return data
