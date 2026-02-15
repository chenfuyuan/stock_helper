"""
概念关系数据库模型。

映射 concept_relation 表，存储概念间的语义关系及追溯上下文。
"""

from datetime import datetime

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    UniqueConstraint,
)

from src.shared.infrastructure.db.base import Base


class ConceptRelationModel(Base):
    """
    概念关系数据库模型。
    
    存储概念间的定向语义关系（上下游、竞争等），作为 Single Source of Truth。
    Neo4j 为派生查询视图，可从此表全量重建。
    """

    __tablename__ = "concept_relation"

    id = Column(Integer, primary_key=True, index=True, comment="主键 ID")
    source_concept_code = Column(
        String(20), nullable=False, index=True, comment="源概念代码"
    )
    target_concept_code = Column(
        String(20), nullable=False, index=True, comment="目标概念代码"
    )
    relation_type = Column(
        String(50),
        nullable=False,
        comment="关系类型（IS_UPSTREAM_OF / IS_DOWNSTREAM_OF / COMPETES_WITH / IS_PART_OF / ENABLER_FOR）",
    )
    source_type = Column(
        String(20), nullable=False, comment="来源类型（MANUAL / LLM）"
    )
    status = Column(
        String(20),
        nullable=False,
        default="PENDING",
        comment="关系状态（PENDING / CONFIRMED / REJECTED）",
    )
    confidence = Column(
        Float, nullable=False, default=1.0, comment="置信度（0.0~1.0，手动创建默认 1.0）"
    )
    ext_info = Column(
        JSON,
        nullable=False,
        default=dict,
        comment="扩展信息（JSONB，存储追溯上下文：手动备注或 LLM 分析详情）",
    )
    created_by = Column(String(100), nullable=True, comment="创建人标识")
    created_at = Column(
        DateTime, nullable=False, default=datetime.now, comment="创建时间"
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.now,
        onupdate=datetime.now,
        comment="更新时间",
    )

    __table_args__ = (
        UniqueConstraint(
            "source_concept_code",
            "target_concept_code",
            "relation_type",
            name="uq_concept_relation",
        ),
        CheckConstraint("confidence >= 0.0 AND confidence <= 1.0", name="ck_confidence"),
    )
