"""
研究会话 ORM 模型，映射表 research_sessions。
"""
import uuid
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID

from src.shared.infrastructure.db.base import Base


class ResearchSessionModel(Base):
    """研究会话表：一次完整研究流水线的元数据与状态。"""

    __tablename__ = "research_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, comment="会话唯一标识")
    symbol = Column(String(20), nullable=False, comment="股票代码")
    status = Column(String(20), nullable=False, comment="running / completed / partial / failed")
    selected_experts = Column(JSONB, nullable=True, comment="选中的专家列表")
    options = Column(JSONB, nullable=True, comment="执行选项")
    trigger_source = Column(String(50), nullable=True, comment="触发来源（api / scheduler）")
    created_at = Column(DateTime, nullable=False, comment="创建时间")
    completed_at = Column(DateTime, nullable=True, comment="完成时间")
    duration_ms = Column(Integer, nullable=True, comment="总耗时（毫秒）")
    retry_count = Column(Integer, nullable=False, default=0, server_default="0", comment="重试计数，首次执行为 0")
    parent_session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("research_sessions.id"),
        nullable=True,
        comment="父会话标识，重试时指向源 session",
    )
