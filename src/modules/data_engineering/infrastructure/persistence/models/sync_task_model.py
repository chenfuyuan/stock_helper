from sqlalchemy import Column, String, Integer, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
import uuid

from src.shared.infrastructure.db.base import Base


class SyncTaskModel(Base):
    """
    同步任务数据库模型
    
    用于持久化同步任务的状态、进度和配置，支持断点续跑和任务互斥。
    """
    __tablename__ = "sync_tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, comment="任务 ID")
    job_type = Column(String(50), nullable=False, index=True, comment="任务类型（DAILY_HISTORY/FINANCE_HISTORY/DAILY_INCREMENTAL/FINANCE_INCREMENTAL）")
    status = Column(String(20), nullable=False, index=True, comment="任务状态（PENDING/RUNNING/COMPLETED/FAILED/PAUSED）")
    current_offset = Column(Integer, nullable=False, default=0, comment="当前同步偏移量（用于分批处理）")
    batch_size = Column(Integer, nullable=False, default=50, comment="每批处理的股票数量")
    total_processed = Column(Integer, nullable=False, default=0, comment="已处理总条数")
    started_at = Column(DateTime, nullable=True, comment="任务启动时间")
    updated_at = Column(DateTime, nullable=True, comment="最后更新时间")
    completed_at = Column(DateTime, nullable=True, comment="任务完成时间")
    config = Column(JSON, nullable=True, comment="任务特定配置（start_date、end_date 等）")
