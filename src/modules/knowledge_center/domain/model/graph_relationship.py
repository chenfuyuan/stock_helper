"""
图谱关系值对象。

定义节点间关系的数据结构。
"""

from pydantic import BaseModel, Field

from src.modules.knowledge_center.domain.model.enums import RelationshipType


class GraphRelationship(BaseModel):
    """
    图谱关系值对象。
    
    描述源节点到目标节点的关系，用于批量构建图谱关系时传递数据。
    """

    source_code: str = Field(..., description="源节点标识（如 Stock 的 third_code）")
    target_name: str = Field(..., description="目标节点名称（如 Industry/Area/Market/Exchange 的 name）")
    relationship_type: RelationshipType = Field(..., description="关系类型枚举")
