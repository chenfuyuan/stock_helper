"""
概念关系同步 DTO。

用于 PostgreSQL → Neo4j 同步过程中传递概念关系数据。
"""

from pydantic import BaseModel, Field


class ConceptRelationSyncDTO(BaseModel):
    """
    概念关系同步 DTO。
    
    用于从 PostgreSQL 读取已确认的概念关系，传递到 Neo4j 进行图谱同步。
    仅包含同步到 Neo4j 所需的字段。
    """

    pg_id: int = Field(description="PostgreSQL 表中的主键 ID（用于反向追溯）")
    source_concept_code: str = Field(description="源概念代码")
    target_concept_code: str = Field(description="目标概念代码")
    relation_type: str = Field(description="关系类型（如 IS_UPSTREAM_OF）")
    source_type: str = Field(description="来源类型（MANUAL 或 LLM）")
    confidence: float = Field(description="置信度（0.0~1.0）")
