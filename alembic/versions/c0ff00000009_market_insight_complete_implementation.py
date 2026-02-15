"""market_insight_complete_implementation

Market Insight 模块完整实现，包含概念表和涨停股表。
合并了 c0ff00000006、c0ff00000007、c0ff00000008 和 f25c663816a5 的功能。

Revision ID: c0ff00000009
Revises: c0ff00000005
Create Date: 2026-02-15

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "c0ff00000009"
down_revision = "c0ff00000005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ----- 概念相关表 -----
    # concept 表
    op.create_table(
        "concept",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="主键ID"),
        sa.Column("code", sa.String(length=50), nullable=False, comment="概念代码"),
        sa.Column("name", sa.String(length=100), nullable=False, comment="概念名称"),
        sa.Column("description", sa.Text(), nullable=True, comment="概念描述"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()"), comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()"), onupdate=sa.text("now()"), comment="更新时间"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_concept_code"),
    )
    op.create_index("ix_concept_code", "concept", ["code"], unique=False)

    # concept_stock 表（概念成分股映射）
    op.create_table(
        "concept_stock",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="主键ID"),
        sa.Column("concept_code", sa.String(length=50), nullable=False, comment="概念代码"),
        sa.Column("third_code", sa.String(length=20), nullable=False, comment="股票代码"),
        sa.Column("stock_name", sa.String(length=100), nullable=False, comment="股票名称"),
        sa.Column("weight", sa.Float(), nullable=True, comment="权重（可选）"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()"), comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()"), onupdate=sa.text("now()"), comment="更新时间"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("concept_code", "third_code", name="uq_concept_stock_code_stock"),
        sa.ForeignKeyConstraint(["concept_code"], ["concept.code"], ondelete="CASCADE"),
    )
    op.create_index("ix_concept_stock_concept_code", "concept_stock", ["concept_code"], unique=False)
    op.create_index("ix_concept_stock_third_code", "concept_stock", ["third_code"], unique=False)

    # ----- Market Insight 表 -----
    # mi_concept_heat（概念热度表）
    op.create_table(
        "mi_concept_heat",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="主键ID"),
        sa.Column("trade_date", sa.Date(), nullable=False, comment="交易日期"),
        sa.Column("concept_code", sa.String(length=50), nullable=False, comment="概念板块代码"),
        sa.Column("concept_name", sa.String(length=100), nullable=False, comment="概念板块名称"),
        sa.Column("avg_pct_chg", sa.Float(), nullable=False, comment="等权平均涨跌幅（百分比）"),
        sa.Column("stock_count", sa.Integer(), nullable=False, comment="成分股总数"),
        sa.Column("up_count", sa.Integer(), nullable=False, comment="上涨家数"),
        sa.Column("down_count", sa.Integer(), nullable=False, comment="下跌家数"),
        sa.Column("limit_up_count", sa.Integer(), nullable=False, comment="涨停家数"),
        sa.Column("total_amount", sa.Float(), nullable=False, comment="板块成交额合计"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()"), comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()"), onupdate=sa.text("now()"), comment="更新时间"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("trade_date", "concept_code", name="uq_mi_concept_heat_date_code"),
    )
    op.create_index("ix_mi_concept_heat_trade_date", "mi_concept_heat", ["trade_date"], unique=False)
    op.create_index("ix_mi_concept_heat_concept_code", "mi_concept_heat", ["concept_code"], unique=False)

    # mi_limit_up_stock（涨停股表）
    op.create_table(
        "mi_limit_up_stock",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="主键ID"),
        sa.Column("trade_date", sa.Date(), nullable=False, comment="交易日期"),
        sa.Column("third_code", sa.String(length=20), nullable=False, comment="股票代码"),
        sa.Column("stock_name", sa.String(length=100), nullable=False, comment="股票名称"),
        sa.Column("pct_chg", sa.Float(), nullable=False, comment="涨跌幅（百分比）"),
        sa.Column("close", sa.Float(), nullable=False, comment="收盘价"),
        sa.Column("amount", sa.Float(), nullable=False, comment="成交额"),
        sa.Column("concepts", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb"), comment="所属概念板块对象列表"),
        sa.Column("limit_type", sa.String(length=20), nullable=False, comment="涨停类型"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()"), comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()"), onupdate=sa.text("now()"), comment="更新时间"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("trade_date", "third_code", name="uq_mi_limit_up_date_code"),
    )
    op.create_index("ix_mi_limit_up_stock_trade_date", "mi_limit_up_stock", ["trade_date"], unique=False)
    op.create_index("ix_mi_limit_up_stock_third_code", "mi_limit_up_stock", ["third_code"], unique=False)


def downgrade() -> None:
    # 删除 Market Insight 表
    op.drop_index("ix_mi_limit_up_stock_third_code", table_name="mi_limit_up_stock")
    op.drop_index("ix_mi_limit_up_stock_trade_date", table_name="mi_limit_up_stock")
    op.drop_table("mi_limit_up_stock")

    op.drop_index("ix_mi_concept_heat_concept_code", table_name="mi_concept_heat")
    op.drop_index("ix_mi_concept_heat_trade_date", table_name="mi_concept_heat")
    op.drop_table("mi_concept_heat")

    # 删除概念相关表
    op.drop_index("ix_concept_stock_third_code", table_name="concept_stock")
    op.drop_index("ix_concept_stock_concept_code", table_name="concept_stock")
    op.drop_table("concept_stock")

    op.drop_index("ix_concept_code", table_name="concept")
    op.drop_table("concept")
