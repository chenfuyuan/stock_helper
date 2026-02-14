from typing import List, Optional
from uuid import UUID

from sqlalchemy import and_, desc, update
from sqlalchemy.future import select

from src.modules.data_engineering.domain.model.enums import (
    SyncJobType,
    SyncTaskStatus,
)
from src.modules.data_engineering.domain.model.sync_failure_record import (
    SyncFailureRecord,
)
from src.modules.data_engineering.domain.model.sync_task import SyncTask
from src.modules.data_engineering.domain.ports.repositories.sync_task_repo import (
    ISyncTaskRepository,
)
from src.modules.data_engineering.infrastructure.persistence.models.sync_failure_model import (
    SyncFailureRecordModel,
)
from src.modules.data_engineering.infrastructure.persistence.models.sync_task_model import (
    SyncTaskModel,
)
from src.shared.infrastructure.base_repository import BaseRepository


class SyncTaskRepositoryImpl(
    BaseRepository[SyncTaskModel], ISyncTaskRepository
):
    """
    同步任务仓储实现

    基于 PostgreSQL 持久化同步任务和失败记录，支持断点续跑、失败重试等场景。
    """

    def __init__(self, session):
        super().__init__(SyncTaskModel, session)

    # ========== SyncTask 相关方法 ==========

    async def create(self, task: SyncTask) -> SyncTask:
        """创建同步任务"""
        task_data = {
            "id": task.id,
            "job_type": task.job_type.value,
            "status": task.status.value,
            "current_offset": task.current_offset,
            "batch_size": task.batch_size,
            "total_processed": task.total_processed,
            "started_at": task.started_at,
            "updated_at": task.updated_at,
            "completed_at": task.completed_at,
            "config": task.config,
        }

        model = SyncTaskModel(**task_data)
        self.session.add(model)
        await self.session.commit()
        await self.session.refresh(model)

        return self._to_sync_task_domain(model)

    async def update(self, task: SyncTask) -> SyncTask:
        """更新同步任务"""
        stmt = (
            update(SyncTaskModel)
            .where(SyncTaskModel.id == task.id)
            .values(
                status=task.status.value,
                current_offset=task.current_offset,
                batch_size=task.batch_size,
                total_processed=task.total_processed,
                started_at=task.started_at,
                updated_at=task.updated_at,
                completed_at=task.completed_at,
                config=task.config,
            )
        )

        await self.session.execute(stmt)
        await self.session.commit()

        # 重新查询返回最新数据
        return await self.get_by_id(task.id)

    async def get_by_id(self, task_id: UUID) -> Optional[SyncTask]:
        """根据 ID 查询任务"""
        result = await self.session.execute(
            select(SyncTaskModel).where(SyncTaskModel.id == task_id)
        )
        model = result.scalar_one_or_none()
        return self._to_sync_task_domain(model) if model else None

    async def get_latest_by_job_type(
        self, job_type: SyncJobType
    ) -> Optional[SyncTask]:
        """查找指定类型的最近一次任务（按 started_at 降序）"""
        result = await self.session.execute(
            select(SyncTaskModel)
            .where(SyncTaskModel.job_type == job_type.value)
            .order_by(desc(SyncTaskModel.started_at))
            .limit(1)
        )
        model = result.scalar_one_or_none()
        return self._to_sync_task_domain(model) if model else None

    # ========== SyncFailureRecord 相关方法 ==========

    async def create_failure(
        self, record: SyncFailureRecord
    ) -> SyncFailureRecord:
        """创建失败记录"""
        record_data = {
            "id": record.id,
            "job_type": record.job_type.value,
            "third_code": record.third_code,
            "error_message": record.error_message,
            "retry_count": record.retry_count,
            "max_retries": record.max_retries,
            "last_attempt_at": record.last_attempt_at,
            "resolved_at": record.resolved_at,
        }

        model = SyncFailureRecordModel(**record_data)
        self.session.add(model)
        await self.session.commit()
        await self.session.refresh(model)

        return self._to_failure_record_domain(model)

    async def update_failure(
        self, record: SyncFailureRecord
    ) -> SyncFailureRecord:
        """更新失败记录"""
        stmt = (
            update(SyncFailureRecordModel)
            .where(SyncFailureRecordModel.id == record.id)
            .values(
                retry_count=record.retry_count,
                last_attempt_at=record.last_attempt_at,
                resolved_at=record.resolved_at,
                error_message=record.error_message,
            )
        )

        await self.session.execute(stmt)
        await self.session.commit()

        # 重新查询返回最新数据
        result = await self.session.execute(
            select(SyncFailureRecordModel).where(
                SyncFailureRecordModel.id == record.id
            )
        )
        model = result.scalar_one_or_none()
        return self._to_failure_record_domain(model) if model else None

    async def get_unresolved_failures(
        self, job_type: SyncJobType
    ) -> List[SyncFailureRecord]:
        """查询未解决且可重试的失败记录"""
        result = await self.session.execute(
            select(SyncFailureRecordModel).where(
                and_(
                    SyncFailureRecordModel.job_type == job_type.value,
                    SyncFailureRecordModel.resolved_at.is_(None),
                    SyncFailureRecordModel.retry_count
                    < SyncFailureRecordModel.max_retries,
                )
            )
        )
        models = result.scalars().all()
        return [self._to_failure_record_domain(model) for model in models]

    async def resolve_failure(self, record_id: UUID) -> None:
        """标记失败记录为已解决"""
        from datetime import datetime

        stmt = (
            update(SyncFailureRecordModel)
            .where(SyncFailureRecordModel.id == record_id)
            .values(resolved_at=datetime.now())
        )

        await self.session.execute(stmt)
        await self.session.commit()

    # ========== 内部转换方法 ==========

    def _to_sync_task_domain(self, model: SyncTaskModel) -> SyncTask:
        """将 ORM 模型转换为 Domain 实体"""
        return SyncTask(
            id=model.id,
            job_type=SyncJobType(model.job_type),
            status=SyncTaskStatus(model.status),
            current_offset=model.current_offset,
            batch_size=model.batch_size,
            total_processed=model.total_processed,
            started_at=model.started_at,
            updated_at=model.updated_at,
            completed_at=model.completed_at,
            config=model.config or {},
        )

    def _to_failure_record_domain(
        self, model: SyncFailureRecordModel
    ) -> SyncFailureRecord:
        """将 ORM 模型转换为 Domain 实体"""
        return SyncFailureRecord(
            id=model.id,
            job_type=SyncJobType(model.job_type),
            third_code=model.third_code,
            error_message=model.error_message,
            retry_count=model.retry_count,
            max_retries=model.max_retries,
            last_attempt_at=model.last_attempt_at,
            resolved_at=model.resolved_at,
        )
