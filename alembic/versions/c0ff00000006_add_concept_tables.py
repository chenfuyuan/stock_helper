"""add_concept_tables

新增 concept 和 concept_stock 表，用于存储概念板块及其成份股映射。

Revision ID: c0ff00000006
Revises: c0ff00000005
Create Date: 2026-02-15

"""

from alembic import op
import sqlalchemy as sa

revision = "c0ff00000006"
down_revision = "c0ff00000005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 创建 concept 表
    op.create_table(
        "concept",
        sa.Column("id", sa.Integer(), nullable=False, comment="主键"),
        sa.Column("code", sa.String(length=20), nullable=False, comment="概念板块代码"),
        sa.Column("name", sa.String(length=100), nullable=False, comment="概念板块名称"),
        sa.Column("created_at", sa.DateTime(), nullable=False, comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, comment="更新时间"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_concept_id"), "concept", ["id"], unique=False)
    op.create_index(op.f("ix_concept_code"), "concept", ["code"], unique=True)

    # 创建 concept_stock 表
    op.create_table(
        "concept_stock",
        sa.Column("id", sa.Integer(), nullable=False, comment="主键"),
        sa.Column("concept_code", sa.String(length=20), nullable=False, comment="概念板块代码"),
        sa.Column(
            "third_code", sa.String(length=20), nullable=False, comment="股票代码（系统标准格式）"
        ),
        sa.Column("stock_name", sa.String(length=100), nullable=True, comment="股票名称"),
        sa.Column("created_at", sa.DateTime(), nullable=False, comment="创建时间"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("concept_code", "third_code", name="uq_concept_stock"),
    )
    op.create_index(op.f("ix_concept_stock_id"), "concept_stock", ["id"], unique=False)
    op.create_index(
        op.f("ix_concept_stock_concept_code"), "concept_stock", ["concept_code"], unique=False
    )
    op.create_index(
        op.f("ix_concept_stock_third_code"), "concept_stock", ["third_code"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_concept_stock_third_code"), table_name="concept_stock")
    op.drop_index(op.f("ix_concept_stock_concept_code"), table_name="concept_stock")
    op.drop_index(op.f("ix_concept_stock_id"), table_name="concept_stock")
    op.drop_table("concept_stock")

    op.drop_index(op.f("ix_concept_code"), table_name="concept")
    op.drop_index(op.f("ix_concept_id"), table_name="concept")
    op.drop_table("concept")
