"""
LLM 调用日志 ORM 模型，映射表 llm_call_logs。
"""

import uuid

from sqlalchemy import Column, DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID

from src.shared.infrastructure.db.base import Base


class LLMCallLogModel(Base):
    """LLM 调用审计表。"""

    __tablename__ = "llm_call_logs"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="记录唯一标识",
    )
    session_id = Column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
        comment="关联 session（无上下文时为 null）",
    )
    caller_module = Column(String(50), nullable=False, comment="调用方模块名")
    caller_agent = Column(
        String(50), nullable=True, comment="调用方 Agent 标识"
    )
    model_name = Column(String(100), nullable=False, comment="模型名称")
    vendor = Column(String(50), nullable=False, comment="供应商")
    prompt_text = Column(Text, nullable=False, comment="完整 user prompt")
    system_message = Column(Text, nullable=True, comment="system prompt")
    completion_text = Column(Text, nullable=True, comment="LLM 完整输出")
    prompt_tokens = Column(Integer, nullable=True, comment="prompt token 数")
    completion_tokens = Column(
        Integer, nullable=True, comment="completion token 数"
    )
    total_tokens = Column(Integer, nullable=True, comment="总 token 数")
    temperature = Column(Float, nullable=False, comment="温度参数")
    latency_ms = Column(Integer, nullable=False, comment="调用耗时（毫秒）")
    status = Column(String(20), nullable=False, comment="success / failed")
    error_message = Column(Text, nullable=True, comment="错误信息")
    created_at = Column(DateTime, nullable=False, comment="记录时间")
