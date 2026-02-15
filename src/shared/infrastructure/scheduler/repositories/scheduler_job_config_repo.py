"""调度器配置仓储实现"""

from typing import Optional, List
from datetime import datetime
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from ..models.scheduler_job_config_model import SchedulerJobConfigModel


class SchedulerJobConfigRepository:
    """调度器配置仓储
    
    提供调度配置的持久化操作，包括查询、创建、更新等。
    """

    def __init__(self, session: AsyncSession):
        """初始化仓储
        
        Args:
            session: 数据库会话
        """
        self._session = session

    async def get_all_enabled(self) -> List[SchedulerJobConfigModel]:
        """获取所有启用的调度配置
        
        Returns:
            启用的配置列表，按 job_id 排序
        """
        stmt = (
            select(SchedulerJobConfigModel)
            .where(SchedulerJobConfigModel.enabled == True)
            .order_by(SchedulerJobConfigModel.job_id)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_job_id(self, job_id: str) -> Optional[SchedulerJobConfigModel]:
        """根据 job_id 查询配置
        
        Args:
            job_id: 任务标识
            
        Returns:
            配置记录，不存在时返回 None
        """
        stmt = select(SchedulerJobConfigModel).where(SchedulerJobConfigModel.job_id == job_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert(
        self,
        job_id: str,
        job_name: str,
        cron_expression: str,
        timezone: str = "Asia/Shanghai",
        enabled: bool = True,
        job_kwargs: Optional[dict] = None,
    ) -> SchedulerJobConfigModel:
        """创建或更新调度配置（upsert 语义）
        
        若 job_id 已存在则更新，否则创建新记录。
        
        Args:
            job_id: 任务标识
            job_name: 任务名称
            cron_expression: cron 表达式
            timezone: 时区，默认 Asia/Shanghai
            enabled: 是否启用，默认 True
            job_kwargs: 任务参数，可选
            
        Returns:
            创建或更新后的配置记录
        """
        now = datetime.utcnow()
        
        stmt = insert(SchedulerJobConfigModel).values(
            job_id=job_id,
            job_name=job_name,
            cron_expression=cron_expression,
            timezone=timezone,
            enabled=enabled,
            job_kwargs=job_kwargs,
            created_at=now,
            updated_at=now,
        )
        
        # ON CONFLICT DO UPDATE
        stmt = stmt.on_conflict_do_update(
            index_elements=["job_id"],
            set_={
                "job_name": job_name,
                "cron_expression": cron_expression,
                "timezone": timezone,
                "enabled": enabled,
                "job_kwargs": job_kwargs,
                "updated_at": now,
            },
        )
        
        await self._session.execute(stmt)
        await self._session.commit()
        
        # 查询并返回最新记录
        config = await self.get_by_job_id(job_id)
        if config is None:
            raise RuntimeError(f"Upsert 后未找到 job_id={job_id} 的配置记录")
        return config

    async def update_enabled(self, job_id: str, enabled: bool) -> None:
        """更新配置的启用状态
        
        Args:
            job_id: 任务标识
            enabled: 是否启用
        """
        stmt = (
            update(SchedulerJobConfigModel)
            .where(SchedulerJobConfigModel.job_id == job_id)
            .values(enabled=enabled, updated_at=datetime.utcnow())
        )
        await self._session.execute(stmt)
        await self._session.commit()

    async def update_last_run_at(self, job_id: str, last_run_at: datetime) -> None:
        """更新最后执行时间
        
        Args:
            job_id: 任务标识
            last_run_at: 最后执行时间
        """
        stmt = (
            update(SchedulerJobConfigModel)
            .where(SchedulerJobConfigModel.job_id == job_id)
            .values(last_run_at=last_run_at, updated_at=datetime.utcnow())
        )
        await self._session.execute(stmt)
        await self._session.commit()
