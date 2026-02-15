"""
概念关系查询 DTO。

用于图谱查询返回概念关系网络和产业链路径。
"""

from pydantic import BaseModel, Field


class ConceptRelationQueryDTO(BaseModel):
    """
    概念关系查询结果 DTO。
    
    用于返回指定概念的直接关系查询结果。
    """

    source_concept_code: str = Field(description="源概念代码")
    target_concept_code: str = Field(description="目标概念代码")
    relation_type: str = Field(description="关系类型")
    source_type: str = Field(description="来源类型（MANUAL 或 LLM）")
    confidence: float = Field(description="置信度（0.0~1.0）")
    pg_id: int | None = Field(default=None, description="PostgreSQL 主键（如果可用）")


class ConceptChainNodeDTO(BaseModel):
    """
    产业链路径节点 DTO。
    
    用于表示产业链遍历路径中的单个节点及其与路径的关系信息。
    """

    concept_code: str = Field(description="概念代码")
    concept_name: str | None = Field(default=None, description="概念名称（如果可用）")
    depth: int = Field(description="从起点的深度（层级）")
    relation_from_previous: str | None = Field(
        default=None, description="与前一个节点的关系类型（起点为 None）"
    )
