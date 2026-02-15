"""调度器配置 ORM 模型"""

import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, String, Boolean, DateTime, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from src.shared.infrastructure.db.base import Base


class SchedulerJobConfigModel(Base):
    """调度器任务配置持久化模型
    
    存储定时任务的配置信息，包括 cron 表达式、启用状态等。
    对应 scheduler_job_config 数据库表。
    """

    __tablename__ = "scheduler_job_config"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, comment="配置唯一标识")
    job_id = Column(String(100), nullable=False, comment="任务标识（对应 JOB_REGISTRY key）")
    job_name = Column(String(200), nullable=False, comment="任务名称（人类可读）")
    cron_expression = Column(String(100), nullable=False, comment="cron 表达式")
    timezone = Column(String(50), nullable=False, server_default="Asia/Shanghai", comment="时区")
    enabled = Column(Boolean, nullable=False, server_default="true", comment="是否启用")
    job_kwargs = Column(JSONB, nullable=True, comment="任务参数（JSON）")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")
    last_run_at = Column(DateTime, nullable=True, comment="最后执行时间")

    __table_args__ = (
        UniqueConstraint("job_id", name="uq_scheduler_job_config_job_id"),
        Index("ix_scheduler_job_config_enabled", "enabled"),
    )

