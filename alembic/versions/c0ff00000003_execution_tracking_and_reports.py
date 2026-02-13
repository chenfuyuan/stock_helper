"""execution_tracking_and_reports

新增 research_sessions、node_executions、llm_call_logs、external_api_call_logs 四张表，
用于研究流水线执行追踪、节点执行记录、LLM 调用审计与外部 API 调用日志。

Revision ID: c0ff00000003
Revises: c0ff00000002
Create Date: 2026-02-13

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "c0ff00000003"
down_revision = "c0ff00000002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ----- research_sessions（Coordinator：研究会话） -----
    op.create_table(
        "research_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, comment="会话唯一标识"),
        sa.Column("symbol", sa.String(length=20), nullable=False, comment="股票代码"),
        sa.Column("status", sa.String(length=20), nullable=False, comment="running / completed / partial / failed"),
        sa.Column("selected_experts", postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment="选中的专家列表"),
        sa.Column("options", postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment="执行选项"),
        sa.Column("trigger_source", sa.String(length=50), nullable=True, comment="触发来源（api / scheduler）"),
        sa.Column("created_at", sa.DateTime(), nullable=False, comment="创建时间"),
        sa.Column("completed_at", sa.DateTime(), nullable=True, comment="完成时间"),
        sa.Column("duration_ms", sa.Integer(), nullable=True, comment="总耗时（毫秒）"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_research_sessions_symbol_created_at",
        "research_sessions",
        ["symbol", "created_at"],
        unique=False,
    )

    # ----- node_executions（Coordinator：节点执行快照） -----
    op.create_table(
        "node_executions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, comment="记录唯一标识"),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False, comment="关联 research_sessions"),
        sa.Column("node_type", sa.String(length=50), nullable=False, comment="节点类型"),
        sa.Column("status", sa.String(length=20), nullable=False, comment="success / failed / skipped"),
        sa.Column("result_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment="结构化业务结果"),
        sa.Column("narrative_report", sa.Text(), nullable=True, comment="文字报告"),
        sa.Column("error_type", sa.String(length=100), nullable=True, comment="异常类名"),
        sa.Column("error_message", sa.Text(), nullable=True, comment="错误详情"),
        sa.Column("started_at", sa.DateTime(), nullable=False, comment="开始时间"),
        sa.Column("completed_at", sa.DateTime(), nullable=True, comment="结束时间"),
        sa.Column("duration_ms", sa.Integer(), nullable=True, comment="节点耗时（毫秒）"),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["session_id"], ["research_sessions.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_node_executions_session_id", "node_executions", ["session_id"], unique=False)

    # ----- llm_call_logs（llm_platform：LLM 调用审计） -----
    op.create_table(
        "llm_call_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, comment="记录唯一标识"),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=True, comment="关联 session（无上下文时为 null）"),
        sa.Column("caller_module", sa.String(length=50), nullable=False, comment="调用方模块名"),
        sa.Column("caller_agent", sa.String(length=50), nullable=True, comment="调用方 Agent 标识"),
        sa.Column("model_name", sa.String(length=100), nullable=False, comment="模型名称"),
        sa.Column("vendor", sa.String(length=50), nullable=False, comment="供应商"),
        sa.Column("prompt_text", sa.Text(), nullable=False, comment="完整 user prompt"),
        sa.Column("system_message", sa.Text(), nullable=True, comment="system prompt"),
        sa.Column("completion_text", sa.Text(), nullable=True, comment="LLM 完整输出"),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True, comment="prompt token 数"),
        sa.Column("completion_tokens", sa.Integer(), nullable=True, comment="completion token 数"),
        sa.Column("total_tokens", sa.Integer(), nullable=True, comment="总 token 数"),
        sa.Column("temperature", sa.Float(), nullable=False, comment="温度参数"),
        sa.Column("latency_ms", sa.Integer(), nullable=False, comment="调用耗时（毫秒）"),
        sa.Column("status", sa.String(length=20), nullable=False, comment="success / failed"),
        sa.Column("error_message", sa.Text(), nullable=True, comment="错误信息"),
        sa.Column("created_at", sa.DateTime(), nullable=False, comment="记录时间"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_llm_call_logs_session_id_created_at",
        "llm_call_logs",
        ["session_id", "created_at"],
        unique=False,
    )

    # ----- external_api_call_logs（shared：外部 API 调用日志） -----
    op.create_table(
        "external_api_call_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, comment="记录唯一标识"),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=True, comment="关联 session"),
        sa.Column("service_name", sa.String(length=50), nullable=False, comment="服务名（bochai / tushare / ...）"),
        sa.Column("operation", sa.String(length=100), nullable=False, comment="操作（web-search / ...）"),
        sa.Column("request_params", postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment="请求参数"),
        sa.Column("response_data", sa.Text(), nullable=True, comment="完整响应"),
        sa.Column("status_code", sa.Integer(), nullable=True, comment="HTTP 状态码"),
        sa.Column("latency_ms", sa.Integer(), nullable=False, comment="调用耗时（毫秒）"),
        sa.Column("status", sa.String(length=20), nullable=False, comment="success / failed"),
        sa.Column("error_message", sa.Text(), nullable=True, comment="错误信息"),
        sa.Column("created_at", sa.DateTime(), nullable=False, comment="记录时间"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_external_api_call_logs_session_id_created_at",
        "external_api_call_logs",
        ["session_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_external_api_call_logs_session_id_created_at", table_name="external_api_call_logs")
    op.drop_table("external_api_call_logs")

    op.drop_index("ix_llm_call_logs_session_id_created_at", table_name="llm_call_logs")
    op.drop_table("llm_call_logs")

    op.drop_index("ix_node_executions_session_id", table_name="node_executions")
    op.drop_table("node_executions")

    op.drop_index("ix_research_sessions_symbol_created_at", table_name="research_sessions")
    op.drop_table("research_sessions")
