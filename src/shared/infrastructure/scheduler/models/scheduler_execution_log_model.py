"""调度执行日志 ORM 模型"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Text, Index
from sqlalchemy.dialects.postgresql import UUID
from src.shared.infrastructure.db.base import Base


class SchedulerExecutionLogModel(Base):
    """调度执行日志持久化模型
    
    记录每次调度任务的执行情况，包括开始/结束时间、状态、错误信息等。
    对应 scheduler_execution_log 数据库表。
    """

    __tablename__ = "scheduler_execution_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, comment="记录唯一标识")
    job_id = Column(String(100), nullable=False, comment="任务标识")
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow, comment="执行开始时间")
    finished_at = Column(DateTime, nullable=True, comment="执行结束时间")
    status = Column(String(20), nullable=False, comment="执行状态（RUNNING / SUCCESS / FAILED）")
    error_message = Column(Text, nullable=True, comment="错误信息")
    duration_ms = Column(Integer, nullable=True, comment="执行耗时（毫秒）")

    __table_args__ = (
        Index("ix_scheduler_execution_log_job_id_started_at", "job_id", "started_at"),
    )
