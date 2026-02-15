"""add_concept_relation_table

新增 concept_relation 表，存储概念间的语义关系（上下游、竞争等）。
PostgreSQL 为 Single Source of Truth，Neo4j 为派生查询视图。

Revision ID: c0ff00000011
Revises: c0ff00000010
Create Date: 2026-02-15

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "c0ff00000011"
down_revision = "c0ff00000010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "concept_relation",
        sa.Column("id", sa.Integer(), nullable=False, comment="主键 ID"),
        sa.Column(
            "source_concept_code",
            sa.String(length=20),
            nullable=False,
            comment="源概念代码",
        ),
        sa.Column(
            "target_concept_code",
            sa.String(length=20),
            nullable=False,
            comment="目标概念代码",
        ),
        sa.Column(
            "relation_type",
            sa.String(length=50),
            nullable=False,
            comment="关系类型（IS_UPSTREAM_OF / IS_DOWNSTREAM_OF / COMPETES_WITH / IS_PART_OF / ENABLER_FOR）",
        ),
        sa.Column(
            "source_type",
            sa.String(length=20),
            nullable=False,
            comment="来源类型（MANUAL / LLM）",
        ),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="PENDING",
            comment="关系状态（PENDING / CONFIRMED / REJECTED）",
        ),
        sa.Column(
            "confidence",
            sa.Float(),
            nullable=False,
            server_default="1.0",
            comment="置信度（0.0~1.0，手动创建默认 1.0）",
        ),
        sa.Column(
            "ext_info",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
            comment="扩展信息（JSONB，存储追溯上下文：手动备注或 LLM 分析详情）",
        ),
        sa.Column("created_by", sa.String(length=100), nullable=True, comment="创建人标识"),
        sa.Column("created_at", sa.DateTime(), nullable=False, comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, comment="更新时间"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_concept_code",
            "target_concept_code",
            "relation_type",
            name="uq_concept_relation",
        ),
        sa.CheckConstraint(
            "confidence >= 0.0 AND confidence <= 1.0", name="ck_confidence"
        ),
    )
    
    # 创建索引以加速查询
    op.create_index(
        "ix_concept_relation_id",
        "concept_relation",
        ["id"],
    )
    op.create_index(
        "ix_concept_relation_source_concept_code",
        "concept_relation",
        ["source_concept_code"],
    )
    op.create_index(
        "ix_concept_relation_target_concept_code",
        "concept_relation",
        ["target_concept_code"],
    )


def downgrade() -> None:
    op.drop_index("ix_concept_relation_target_concept_code", table_name="concept_relation")
    op.drop_index("ix_concept_relation_source_concept_code", table_name="concept_relation")
    op.drop_index("ix_concept_relation_id", table_name="concept_relation")
    op.drop_table("concept_relation")
