"""add_sync_tables

新增 sync_tasks 和 sync_failure_records 表，用于同步任务状态管理和失败记录追踪。

Revision ID: c0ff00000002
Revises: c0ff00000001
Create Date: 2026-02-12

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "c0ff00000002"
down_revision = "c0ff00000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ----- sync_tasks（data_engineering：同步任务状态） -----
    op.create_table(
        "sync_tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, comment="任务 ID"),
        sa.Column(
            "job_type",
            sa.String(length=50),
            nullable=False,
            comment="任务类型（DAILY_HISTORY/FINANCE_HISTORY/DAILY_INCREMENTAL/FINANCE_INCREMENTAL）",
        ),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            comment="任务状态（PENDING/RUNNING/COMPLETED/FAILED/PAUSED）",
        ),
        sa.Column(
            "current_offset",
            sa.Integer(),
            nullable=False,
            server_default="0",
            comment="当前同步偏移量（用于分批处理）",
        ),
        sa.Column(
            "batch_size",
            sa.Integer(),
            nullable=False,
            server_default="50",
            comment="每批处理的股票数量",
        ),
        sa.Column(
            "total_processed",
            sa.Integer(),
            nullable=False,
            server_default="0",
            comment="已处理总条数",
        ),
        sa.Column("started_at", sa.DateTime(), nullable=True, comment="任务启动时间"),
        sa.Column("updated_at", sa.DateTime(), nullable=True, comment="最后更新时间"),
        sa.Column("completed_at", sa.DateTime(), nullable=True, comment="任务完成时间"),
        sa.Column(
            "config",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=True,
            comment="任务特定配置（start_date、end_date 等）",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_sync_tasks_job_type"), "sync_tasks", ["job_type"], unique=False)
    op.create_index(op.f("ix_sync_tasks_status"), "sync_tasks", ["status"], unique=False)

    # ----- sync_failure_records（data_engineering：同步失败记录） -----
    op.create_table(
        "sync_failure_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, comment="失败记录 ID"),
        sa.Column(
            "job_type",
            sa.String(length=50),
            nullable=False,
            comment="任务类型（DAILY_HISTORY/FINANCE_HISTORY/DAILY_INCREMENTAL/FINANCE_INCREMENTAL）",
        ),
        sa.Column(
            "third_code",
            sa.String(length=20),
            nullable=False,
            comment="失败的股票代码（Tushare ts_code 格式）",
        ),
        sa.Column("error_message", sa.String(length=500), nullable=True, comment="错误信息"),
        sa.Column(
            "retry_count", sa.Integer(), nullable=False, server_default="0", comment="当前重试次数"
        ),
        sa.Column(
            "max_retries", sa.Integer(), nullable=False, server_default="3", comment="最大重试次数"
        ),
        sa.Column("last_attempt_at", sa.DateTime(), nullable=True, comment="最后一次尝试时间"),
        sa.Column(
            "resolved_at", sa.DateTime(), nullable=True, comment="解决时间（重试成功或人工标记）"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_sync_failure_records_job_type"), "sync_failure_records", ["job_type"], unique=False
    )
    op.create_index(
        op.f("ix_sync_failure_records_third_code"),
        "sync_failure_records",
        ["third_code"],
        unique=False,
    )
    op.create_index(
        op.f("ix_sync_failure_records_resolved_at"),
        "sync_failure_records",
        ["resolved_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_sync_failure_records_resolved_at"), table_name="sync_failure_records")
    op.drop_index(op.f("ix_sync_failure_records_third_code"), table_name="sync_failure_records")
    op.drop_index(op.f("ix_sync_failure_records_job_type"), table_name="sync_failure_records")
    op.drop_table("sync_failure_records")

    op.drop_index(op.f("ix_sync_tasks_status"), table_name="sync_tasks")
    op.drop_index(op.f("ix_sync_tasks_job_type"), table_name="sync_tasks")
    op.drop_table("sync_tasks")
