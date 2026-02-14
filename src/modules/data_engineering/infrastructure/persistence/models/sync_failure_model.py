import uuid

from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import UUID

from src.shared.infrastructure.db.base import Base


class SyncFailureRecordModel(Base):
    """
    同步失败记录数据库模型

    用于记录单只股票在同步过程中的失败信息，支持自动重试机制。
    """

    __tablename__ = "sync_failure_records"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="失败记录 ID",
    )
    job_type = Column(
        String(50),
        nullable=False,
        index=True,
        comment="任务类型（DAILY_HISTORY/FINANCE_HISTORY/DAILY_INCREMENTAL/FINANCE_INCREMENTAL）",
    )
    third_code = Column(
        String(20),
        nullable=False,
        index=True,
        comment="失败的股票代码（Tushare ts_code 格式）",
    )
    error_message = Column(String(500), nullable=True, comment="错误信息")
    retry_count = Column(
        Integer, nullable=False, default=0, comment="当前重试次数"
    )
    max_retries = Column(
        Integer, nullable=False, default=3, comment="最大重试次数"
    )
    last_attempt_at = Column(
        DateTime, nullable=True, comment="最后一次尝试时间"
    )
    resolved_at = Column(
        DateTime,
        nullable=True,
        index=True,
        comment="解决时间（重试成功或人工标记）",
    )
