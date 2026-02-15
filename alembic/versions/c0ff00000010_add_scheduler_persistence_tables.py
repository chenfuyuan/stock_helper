"""add_scheduler_persistence_tables

新增 scheduler_job_config 和 scheduler_execution_log 两张表，
用于调度器配置持久化和执行历史记录。同时 seed 默认调度配置。

Revision ID: c0ff00000010
Revises: c0ff00000009
Create Date: 2026-02-15

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "c0ff00000010"
down_revision = "c0ff00000009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ----- scheduler_job_config（调度器配置表） -----
    op.create_table(
        "scheduler_job_config",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, comment="配置唯一标识"),
        sa.Column("job_id", sa.String(length=100), nullable=False, comment="任务标识（对应 JOB_REGISTRY key）"),
        sa.Column("job_name", sa.String(length=200), nullable=False, comment="任务名称（人类可读）"),
        sa.Column("cron_expression", sa.String(length=100), nullable=False, comment="cron 表达式"),
        sa.Column("timezone", sa.String(length=50), nullable=False, server_default="Asia/Shanghai", comment="时区"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true", comment="是否启用"),
        sa.Column(
            "job_kwargs",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="任务参数（JSON）",
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False, comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, comment="更新时间"),
        sa.Column("last_run_at", sa.DateTime(), nullable=True, comment="最后执行时间"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_id", name="uq_scheduler_job_config_job_id"),
    )
    op.create_index(
        "ix_scheduler_job_config_enabled",
        "scheduler_job_config",
        ["enabled"],
        unique=False,
    )

    # ----- scheduler_execution_log（调度执行记录表） -----
    op.create_table(
        "scheduler_execution_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, comment="记录唯一标识"),
        sa.Column("job_id", sa.String(length=100), nullable=False, comment="任务标识"),
        sa.Column("started_at", sa.DateTime(), nullable=False, comment="执行开始时间"),
        sa.Column("finished_at", sa.DateTime(), nullable=True, comment="执行结束时间"),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            comment="执行状态（RUNNING / SUCCESS / FAILED）",
        ),
        sa.Column("error_message", sa.Text(), nullable=True, comment="错误信息"),
        sa.Column("duration_ms", sa.Integer(), nullable=True, comment="执行耗时（毫秒）"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_scheduler_execution_log_job_id_started_at",
        "scheduler_execution_log",
        ["job_id", "started_at"],
        unique=False,
    )

    # ----- Seed 默认调度配置 -----
    # 使用原生 SQL 的 INSERT ... ON CONFLICT DO NOTHING 保证幂等
    op.execute(
        """
        INSERT INTO scheduler_job_config (id, job_id, job_name, cron_expression, timezone, enabled, job_kwargs, created_at, updated_at)
        VALUES
            (gen_random_uuid(), 'sync_daily_by_date', '日线增量同步', '0 18 * * *', 'Asia/Shanghai', true, NULL, NOW(), NOW()),
            (gen_random_uuid(), 'sync_incremental_finance', '财务增量同步', '0 0 * * *', 'Asia/Shanghai', true, NULL, NOW(), NOW()),
            (gen_random_uuid(), 'sync_concept_data', '概念数据同步', '30 18 * * *', 'Asia/Shanghai', true, NULL, NOW(), NOW()),
            (gen_random_uuid(), 'sync_stock_basic', '股票基础信息同步', '0 19 * * *', 'Asia/Shanghai', true, NULL, NOW(), NOW())
        ON CONFLICT (job_id) DO NOTHING;
        """
    )


def downgrade() -> None:
    op.drop_index("ix_scheduler_execution_log_job_id_started_at", table_name="scheduler_execution_log")
    op.drop_table("scheduler_execution_log")

    op.drop_index("ix_scheduler_job_config_enabled", table_name="scheduler_job_config")
    op.drop_table("scheduler_job_config")
