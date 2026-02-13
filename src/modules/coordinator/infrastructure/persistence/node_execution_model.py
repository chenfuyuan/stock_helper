"""
节点执行 ORM 模型，映射表 node_executions。
"""
import uuid
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from src.shared.infrastructure.db.base import Base


class NodeExecutionModel(Base):
    """节点执行表：LangGraph 各节点执行快照（含成功/失败）。"""

    __tablename__ = "node_executions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, comment="记录唯一标识")
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("research_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="关联 research_sessions",
    )
    node_type = Column(String(50), nullable=False, comment="节点类型")
    status = Column(String(20), nullable=False, comment="success / failed / skipped")
    result_data = Column(JSONB, nullable=True, comment="结构化业务结果")
    narrative_report = Column(Text, nullable=True, comment="文字报告")
    error_type = Column(String(100), nullable=True, comment="异常类名")
    error_message = Column(Text, nullable=True, comment="错误详情")
    started_at = Column(DateTime, nullable=False, comment="开始时间")
    completed_at = Column(DateTime, nullable=True, comment="结束时间")
    duration_ms = Column(Integer, nullable=True, comment="节点耗时（毫秒）")
