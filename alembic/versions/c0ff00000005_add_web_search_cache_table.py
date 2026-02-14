"""add_web_search_cache_table

新增 web_search_cache 表，用于博查搜索结果缓存（cache_key PK、request_params JSONB、
response_data TEXT、created_at/expires_at + expires_at 索引）。

Revision ID: c0ff00000005
Revises: c0ff00000004
Create Date: 2026-02-14

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "c0ff00000005"
down_revision = "c0ff00000004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "web_search_cache",
        sa.Column("cache_key", sa.String(length=64), nullable=False, comment="请求参数 SHA-256 哈希，主键"),
        sa.Column("request_params", postgresql.JSONB(astext_type=sa.Text()), nullable=False, comment="原始请求参数"),
        sa.Column("response_data", sa.Text(), nullable=False, comment="WebSearchResponse JSON"),
        sa.Column("created_at", sa.DateTime(), nullable=False, comment="写入时间"),
        sa.Column("expires_at", sa.DateTime(), nullable=False, comment="过期时间"),
        sa.PrimaryKeyConstraint("cache_key"),
    )
    op.create_index(
        op.f("ix_web_search_cache_expires_at"),
        "web_search_cache",
        ["expires_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_web_search_cache_expires_at"), table_name="web_search_cache")
    op.drop_table("web_search_cache")
