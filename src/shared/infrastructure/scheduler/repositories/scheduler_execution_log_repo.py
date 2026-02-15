"""调度执行日志仓储实现"""

import uuid
from typing import Optional, List
from datetime import datetime
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.scheduler_execution_log_model import SchedulerExecutionLogModel


class SchedulerExecutionLogRepository:
    """调度执行日志仓储
    
    提供执行日志的持久化操作，包括创建、更新、查询等。
    """

    def __init__(self, session: AsyncSession):
        """初始化仓储
        
        Args:
            session: 数据库会话
        """
        self._session = session

    async def create(
        self,
        job_id: str,
        started_at: datetime,
        status: str = "RUNNING",
    ) -> SchedulerExecutionLogModel:
        """创建执行日志记录
        
        Args:
            job_id: 任务标识
            started_at: 开始时间
            status: 初始状态，默认 RUNNING
            
        Returns:
            创建的日志记录
        """
        import uuid
        log = SchedulerExecutionLogModel(
            id=uuid.uuid4(),
            job_id=job_id,
            execution_id=str(uuid.uuid4()),  # 生成执行ID
            started_at=started_at,
            status=status,
            created_at=started_at,
            updated_at=started_at,
        )
        self._session.add(log)
        await self._session.commit()
        await self._session.refresh(log)
        return log

    async def update(
        self,
        log_id: uuid.UUID,
        status: str,
        finished_at: Optional[datetime] = None,
        error_message: Optional[str] = None,
        duration_ms: Optional[int] = None,
    ) -> None:
        """更新执行日志记录
        
        Args:
            log_id: 日志记录 ID
            status: 执行状态（SUCCESS / FAILED）
            finished_at: 结束时间，可选
            error_message: 错误信息，可选
            duration_ms: 执行耗时（毫秒），可选
        """
        values = {"status": status}
        if finished_at is not None:
            values["finished_at"] = finished_at
        if error_message is not None:
            values["error_message"] = error_message
        if duration_ms is not None:
            values["duration_ms"] = duration_ms

        stmt = (
            update(SchedulerExecutionLogModel)
            .where(SchedulerExecutionLogModel.id == log_id)
            .values(**values)
        )
        await self._session.execute(stmt)
        await self._session.commit()

    async def get_recent_by_job_id(
        self,
        job_id: str,
        limit: int = 20,
    ) -> List[SchedulerExecutionLogModel]:
        """查询指定任务的最近执行记录
        
        Args:
            job_id: 任务标识
            limit: 返回记录数量上限，默认 20
            
        Returns:
            执行记录列表，按 started_at 降序排列
        """
        stmt = (
            select(SchedulerExecutionLogModel)
            .where(SchedulerExecutionLogModel.job_id == job_id)
            .order_by(SchedulerExecutionLogModel.started_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_recent_all(self, limit: int = 20) -> List[SchedulerExecutionLogModel]:
        """查询所有任务的最近执行记录
        
        Args:
            limit: 返回记录数量上限，默认 20
            
        Returns:
            执行记录列表，按 started_at 降序排列
        """
        stmt = (
            select(SchedulerExecutionLogModel)
            .order_by(SchedulerExecutionLogModel.started_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
