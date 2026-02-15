"""
概念关系领域实体。

定义概念间的语义关系，包含关系类型、来源、状态、置信度等核心字段。
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from .enums import ConceptRelationType, RelationSourceType, RelationStatus


class ConceptRelation(BaseModel):
    """
    概念关系领域实体。
    
    表示两个概念节点之间的定向语义关系（如上下游、竞争等）。
    
    核心约束：
    - source_concept_code 和 target_concept_code + relation_type 组合唯一
    - confidence 范围 [0.0, 1.0]
    - 手动创建的关系默认 confidence=1.0, status=CONFIRMED
    - LLM 推荐的关系默认 status=PENDING，需人工确认
    - ext_info 存储追溯上下文（手动备注或 LLM 分析详情）
    """

    id: int | None = None
    source_concept_code: str = Field(description="源概念代码")
    target_concept_code: str = Field(description="目标概念代码")
    relation_type: ConceptRelationType = Field(description="关系类型")
    source_type: RelationSourceType = Field(description="来源类型")
    status: RelationStatus = Field(
        default=RelationStatus.PENDING, description="关系状态"
    )
    confidence: float = Field(
        default=1.0, ge=0.0, le=1.0, description="置信度（0.0~1.0）"
    )
    ext_info: dict[str, Any] = Field(
        default_factory=dict, description="扩展信息（JSONB，存储追溯上下文）"
    )
    created_by: str | None = Field(default=None, description="创建人标识")
    created_at: datetime | None = Field(default=None, description="创建时间")
    updated_at: datetime | None = Field(default=None, description="更新时间")

    @field_validator("source_type")
    @classmethod
    def set_default_status_by_source(cls, v: RelationSourceType, info) -> RelationSourceType:
        """
        根据来源类型设置默认状态。
        
        手动创建的关系默认为 CONFIRMED，LLM 推荐的默认为 PENDING。
        注意：此校验器仅处理来源类型本身，状态的设置在创建时由业务逻辑处理。
        """
        return v

    class Config:
        """Pydantic 配置。"""

        use_enum_values = True
        json_encoders = {datetime: lambda v: v.isoformat()}
