"""调度器配置仓储实现"""

from typing import Optional, List
from datetime import datetime
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from ..models.scheduler_job_config_model import SchedulerJobConfigModel
from src.modules.foundation.domain.ports.scheduler_job_config_repository_port import SchedulerJobConfigRepositoryPort
from src.modules.foundation.domain.dtos.scheduler_dtos import JobConfigDTO


class SchedulerJobConfigRepository(SchedulerJobConfigRepositoryPort):
    """调度器配置仓储
    
    提供调度配置的持久化操作，包括查询、创建、更新等。
    """

    def __init__(self, session: AsyncSession):
        """初始化仓储
        
        Args:
            session: 数据库会话
        """
        self._session = session

    async def get_all_enabled(self) -> List[JobConfigDTO]:
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
        models = list(result.scalars().all())
        return [self._model_to_dto(model) for model in models]

    async def get_by_job_id(self, job_id: str) -> Optional[JobConfigDTO]:
        """根据 job_id 查询配置
        
        Args:
            job_id: 任务标识
            
        Returns:
            配置记录，不存在时返回 None
        """
        stmt = select(SchedulerJobConfigModel).where(SchedulerJobConfigModel.job_id == job_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._model_to_dto(model) if model else None

    async def create(self, job_config: JobConfigDTO) -> JobConfigDTO:
        """创建新的调度配置
        
        Args:
            job_config: 要创建的配置
            
        Returns:
            创建后的配置（包含生成的字段）
        """
        now = datetime.utcnow()
        model = SchedulerJobConfigModel(
            job_id=job_config.job_id,
            job_name=job_config.job_name,
            cron_expression=job_config.cron_expression,
            timezone=job_config.timezone,
            enabled=job_config.enabled,
            job_kwargs=job_config.job_kwargs,
            created_at=now,
            updated_at=now,
        )
        
        self._session.add(model)
        await self._session.commit()
        await self._session.refresh(model)
        
        return self._model_to_dto(model)
    async def update(self, job_config: JobConfigDTO) -> JobConfigDTO:
        """更新调度配置
        
        Args:
            job_config: 要更新的配置
            
        Returns:
            更新后的配置
        """
        stmt = (
            update(SchedulerJobConfigModel)
            .where(SchedulerJobConfigModel.job_id == job_config.job_id)
            .values(
                job_name=job_config.job_name,
                cron_expression=job_config.cron_expression,
                timezone=job_config.timezone,
                enabled=job_config.enabled,
                job_kwargs=job_config.job_kwargs,
                updated_at=datetime.utcnow(),
            )
        )
        await self._session.execute(stmt)
        await self._session.commit()
        
        updated = await self.get_by_job_id(job_config.job_id)
        if updated is None:
            raise RuntimeError(f"更新后未找到 job_id={job_config.job_id} 的配置记录")
        return updated

    async def upsert(self, job_config: JobConfigDTO) -> JobConfigDTO:
        """创建或更新调度配置（upsert 操作）
        
        Args:
            job_config: 要创建或更新的配置
            
        Returns:
            创建或更新后的配置
        """
        existing = await self.get_by_job_id(job_config.job_id)
        if existing:
            return await self.update(job_config)
        else:
            return await self.create(job_config)

    async def update_enabled(self, job_id: str, enabled: bool) -> bool:
        """更新任务的启用状态
        
        Args:
            job_id: 任务标识
            enabled: 是否启用
            
        Returns:
            是否成功更新
        """
        stmt = (
            update(SchedulerJobConfigModel)
            .where(SchedulerJobConfigModel.job_id == job_id)
            .values(enabled=enabled, updated_at=datetime.utcnow())
        )
        result = await self._session.execute(stmt)
        await self._session.commit()
        return result.rowcount > 0

    async def delete(self, job_id: str) -> bool:
        """删除调度配置
        
        Args:
            job_id: 要删除的任务标识
            
        Returns:
            是否成功删除
        """
        stmt = delete(SchedulerJobConfigModel).where(SchedulerJobConfigModel.job_id == job_id)
        result = await self._session.execute(stmt)
        await self._session.commit()
        return result.rowcount > 0

    # 保留原有方法以兼容现有代码
    async def upsert(
        self,
        job_id: str,
        job_name: str,
        cron_expression: str,
        timezone: str = "Asia/Shanghai",
        enabled: bool = True,
        job_kwargs: Optional[dict] = None,
    ) -> JobConfigDTO:
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
        job_config = JobConfigDTO(
            job_id=job_id,
            job_name=job_name,
            cron_expression=cron_expression,
            timezone=timezone,
            enabled=enabled,
            job_kwargs=job_kwargs or {}
        )
        
        existing = await self.get_by_job_id(job_id)
        if existing:
            return await self.update(job_config)
        else:
            return await self.create(job_config)

    def _model_to_dto(self, model: SchedulerJobConfigModel) -> JobConfigDTO:
        """将 ORM 模型转换为 DTO
        
        Args:
            model: ORM 模型实例
            
        Returns:
            DTO 实例
        """
        return JobConfigDTO(
            job_id=model.job_id,
            job_name=model.job_name,
            cron_expression=model.cron_expression,
            timezone=model.timezone,
            enabled=model.enabled,
            job_kwargs=model.job_kwargs or {}
        )
