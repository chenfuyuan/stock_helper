from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from src.modules.data_engineering.domain.model.enums import (
    SyncJobType,
    SyncTaskStatus,
)


@dataclass
class SyncTask:
    """
    同步任务实体

    用于追踪同步任务的生命周期、进度和状态。支持断点续跑和并发互斥控制。
    """

    id: UUID = field(default_factory=uuid4)
    job_type: SyncJobType = SyncJobType.DAILY_HISTORY
    status: SyncTaskStatus = SyncTaskStatus.PENDING
    current_offset: int = 0  # 当前同步偏移量（用于历史全量同步的分批处理）
    batch_size: int = 50  # 每批处理的股票数量
    total_processed: int = 0  # 已处理总条数
    started_at: Optional[datetime] = None  # 任务启动时间
    updated_at: Optional[datetime] = None  # 最后更新时间
    completed_at: Optional[datetime] = None  # 任务完成时间
    config: Dict[str, Any] = field(
        default_factory=dict
    )  # 任务特定配置（如 start_date、end_date 等）

    def start(self) -> None:
        """启动任务：更新状态为 RUNNING 并记录启动时间"""
        self.status = SyncTaskStatus.RUNNING
        self.started_at = datetime.now()
        self.updated_at = datetime.now()

    def update_progress(self, processed_count: int, new_offset: int) -> None:
        """
        更新任务进度

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
