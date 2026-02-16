"""
同步任务领域实体。

追踪同步任务的生命周期、进度和状态，支持断点续跑和并发互斥控制。
从 dataclass 迁移为 Pydantic BaseModel，统一领域建模约定。
"""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from pydantic import ConfigDict, Field

from src.modules.data_engineering.domain.model.enums import (
    SyncJobType,
    SyncTaskStatus,
)
from src.shared.domain.base_entity import BaseEntity


class SyncTask(BaseEntity):
    """
    同步任务实体。

    用于追踪同步任务的生命周期、进度和状态。支持断点续跑和并发互斥控制。
    """

    job_type: SyncJobType = Field(default=SyncJobType.DAILY_HISTORY, description="任务类型")
    status: SyncTaskStatus = Field(default=SyncTaskStatus.PENDING, description="任务状态")
    current_offset: int = Field(default=0, description="当前同步偏移量（用于历史全量同步的分批处理）")
    batch_size: int = Field(default=50, description="每批处理的股票数量")
    total_processed: int = Field(default=0, description="已处理总条数")
    started_at: Optional[datetime] = Field(default=None, description="任务启动时间")
    completed_at: Optional[datetime] = Field(default=None, description="任务完成时间")
    config: Dict[str, Any] = Field(default_factory=dict, description="任务特定配置（如 start_date、end_date 等）")

    model_config = ConfigDict(from_attributes=True)

    def start(self) -> None:
        """启动任务：更新状态为 RUNNING 并记录启动时间"""
        self.status = SyncTaskStatus.RUNNING
        self.started_at = datetime.now()
        self.updated_at = datetime.now()

    def update_progress(self, processed_count: int, new_offset: int) -> None:
        """
        更新任务进度。

        Args:
            processed_count: 本批处理的条数
            new_offset: 新的偏移量（下次从这里继续）
        """
        self.total_processed += processed_count
        self.current_offset = new_offset
        self.updated_at = datetime.now()

    def complete(self) -> None:
        """标记任务为完成状态"""
        self.status = SyncTaskStatus.COMPLETED
        self.completed_at = datetime.now()
        self.updated_at = datetime.now()

    def fail(self) -> None:
        """标记任务为失败状态"""
        self.status = SyncTaskStatus.FAILED
        self.updated_at = datetime.now()

    def pause(self) -> None:
        """暂停任务"""
        self.status = SyncTaskStatus.PAUSED
        self.updated_at = datetime.now()

    def is_resumable(self) -> bool:
        """判断任务是否可恢复（RUNNING 或 PAUSED 状态）"""
        return self.status in (SyncTaskStatus.RUNNING, SyncTaskStatus.PAUSED)
