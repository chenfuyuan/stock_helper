from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from src.modules.data_engineering.domain.model.enums import SyncJobType
from src.modules.data_engineering.domain.model.sync_failure_record import (
    SyncFailureRecord,
)
from src.modules.data_engineering.domain.model.sync_task import SyncTask


class ISyncTaskRepository(ABC):
    """
    同步任务仓储接口

    负责管理同步任务和失败记录的持久化，支持断点续跑、失败重试等场景。
    """

    @abstractmethod
    async def create(self, task: SyncTask) -> SyncTask:
        """
        创建同步任务

        Args:
            task: 同步任务实体

        Returns:
            创建后的任务（包含生成的 ID 等信息）
        """

    @abstractmethod
    async def update(self, task: SyncTask) -> SyncTask:
        """
        更新同步任务

        Args:
            task: 待更新的任务实体

        Returns:
            更新后的任务
        """

    @abstractmethod
    async def get_by_id(self, task_id: UUID) -> Optional[SyncTask]:
        """
        根据 ID 查询任务

        Args:
            task_id: 任务 ID

        Returns:
            任务实体，不存在时返回 None
        """

    @abstractmethod
    async def get_latest_by_job_type(
        self, job_type: SyncJobType
    ) -> Optional[SyncTask]:
        """
        查找指定类型的最近一次任务（按 started_at 降序）

        用于断点续跑场景：查找最近的 RUNNING 或 PAUSED 任务。

        Args:
            job_type: 任务类型

        Returns:
            最近的任务实体，不存在时返回 None
        """

    @abstractmethod
    async def create_failure(
        self, record: SyncFailureRecord
    ) -> SyncFailureRecord:
        """
        创建失败记录

        Args:
            record: 失败记录实体

        Returns:
            创建后的失败记录
        """

    @abstractmethod
    async def update_failure(
        self, record: SyncFailureRecord
    ) -> SyncFailureRecord:
        """
        更新失败记录（用于递增重试次数、标记已解决等）

        Args:
            record: 待更新的失败记录实体

        Returns:
            更新后的失败记录
        """

    @abstractmethod
    async def get_unresolved_failures(
        self, job_type: SyncJobType
    ) -> List[SyncFailureRecord]:
        """
        查询未解决且可重试的失败记录

        条件：resolved_at IS NULL AND retry_count < max_retries AND job_type 匹配

        Args:
            job_type: 任务类型

        Returns:
            失败记录列表
        """

    @abstractmethod
    async def resolve_failure(self, record_id: UUID) -> None:
        """
        标记失败记录为已解决

        Args:
            record_id: 失败记录 ID
        """
