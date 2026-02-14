"""add_retry_fields_to_research_sessions

research_sessions 表新增 retry_count（重试计数）和 parent_session_id（父会话标识）列，
支持研究任务手动重试能力。

Revision ID: c0ff00000004
Revises: c0ff00000003
Create Date: 2026-02-14

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "c0ff00000004"
down_revision = "c0ff00000003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "research_sessions",
        sa.Column(
            "retry_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
            comment="重试计数，首次执行为 0",
        ),
    )
    op.add_column(
        "research_sessions",
        sa.Column(
            "parent_session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("research_sessions.id"),
            nullable=True,
            comment="父会话标识，重试时指向源 session",
        ),
    )


def downgrade() -> None:
    op.drop_column("research_sessions", "parent_session_id")
    op.drop_column("research_sessions", "retry_count")
