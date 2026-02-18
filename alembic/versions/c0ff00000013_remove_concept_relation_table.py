"""remove_concept_relation_table

删除 concept_relation 表及相关功能，移除概念关系管理功能。
基于设计决策：概念关系功能基于错误假设，将不同维度的概念混为一谈建立伪产业链关系。

Revision ID: c0ff00000013
Revises: c0ff00000012
Create Date: 2026-02-19

"""

from alembic import op
import sqlalchemy as sa

revision = "c0ff00000013"
down_revision = "c0ff00000012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 删除索引
    op.drop_index("ix_concept_relation_target_concept_code", table_name="concept_relation")
    op.drop_index("ix_concept_relation_source_concept_code", table_name="concept_relation")
    op.drop_index("ix_concept_relation_id", table_name="concept_relation")
    
    # 删除表
    op.drop_table("concept_relation")


def downgrade() -> None:
    # 重建表（用于回滚）
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
            sa.dialects.postgresql.JSONB(astext_type=sa.Text()),
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
    
    # 重建索引
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
