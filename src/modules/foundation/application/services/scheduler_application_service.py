"""调度器应用服务

提供调度器的业务编排逻辑，负责数据加载、持久化和任务管理。
通过依赖注入使用 SchedulerPort，不直接依赖具体实现。
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from src.modules.foundation.domain.ports.scheduler_port import SchedulerPort
from src.modules.foundation.domain.ports.scheduler_job_config_repository_port import SchedulerJobConfigRepositoryPort
from src.modules.foundation.domain.dtos.scheduler_dtos import (
    JobConfigDTO,
    JobStatusDTO,
    SchedulerConfigDTO
)
from src.modules.foundation.domain.exceptions import (
    SchedulerException,
    SchedulerJobNotFoundException,
    SchedulerJobAlreadyExistsException,
    SchedulerConfigurationException,
    SchedulerExecutionException
)
from src.modules.foundation.domain.types import (
    JobRegistry,
    JobId,
    JobFunction
)

logger = logging.getLogger(__name__)


class SchedulerApplicationService:
    """调度器应用服务
    
    负责调度器的业务编排，包括任务管理、配置加载和状态查询。
    通过 Port 接口与基础设施解耦，便于测试和替换实现。
    """

    def __init__(
        self,
        scheduler_port: SchedulerPort,
        scheduler_job_config_repo_port: SchedulerJobConfigRepositoryPort,
        scheduler_execution_log_repo_port: Optional[Any] = None
    ):
        """初始化调度器应用服务
        
        Args:
            scheduler_port: 调度器端口接口
            scheduler_job_config_repo_port: 调度配置仓储端口接口
            scheduler_execution_log_repo_port: 执行日志仓储端口接口（可选）
        """
        self._scheduler_port = scheduler_port
        self._scheduler_job_config_repo_port = scheduler_job_config_repo_port
        self._scheduler_execution_log_repo_port = scheduler_execution_log_repo_port

    async def start_scheduler(self) -> None:
        """启动调度器
        
        启动调度器的后台任务循环。
        如果启动失败，会记录错误并重新抛出异常。
        """
        try:
            logger.info("启动调度器...")
            await self._scheduler_port.start_scheduler()
            logger.info("调度器启动成功")
        except Exception as e:
            logger.error(f"启动调度器失败: {str(e)}")
            raise

    async def shutdown_scheduler(self) -> None:
        """关闭调度器
        
        优雅关闭调度器，停止所有正在运行的任务。
        """
        try:
            logger.info("关闭调度器...")
            await self._scheduler_port.shutdown_scheduler()
            logger.info("调度器关闭成功")
        except Exception as e:
            logger.error(f"关闭调度器失败: {str(e)}")
            raise

    async def schedule_job(
        self,
        job_config: JobConfigDTO,
        job_registry: JobRegistry
    ) -> None:
        """调度定时任务
        
        Args:
            job_config: 任务配置
            job_registry: 任务函数注册表
            
        Raises:
            SchedulerJobNotFoundException: 任务函数未找到
            SchedulerJobAlreadyExistsException: 任务已存在
            SchedulerConfigurationException: 配置无效
        """
        # 验证任务配置
        self._validate_job_config(job_config)
        
        # 检查任务函数是否在注册表中
        job_func = job_registry.get(job_config.job_id)
        if job_func is None:
            raise SchedulerJobNotFoundException(job_config.job_id)
        
        try:
            # 通过端口调度任务
            await self._scheduler_port.schedule_job(
                job_id=job_config.job_id,
                job_func=job_func,
                cron_expression=job_config.cron_expression,
                timezone=job_config.timezone,
                **job_config.job_kwargs
            )
            
            logger.info(
                f"任务调度成功: {job_config.job_id} - {job_config.cron_expression}"
            )
            
        except SchedulerJobAlreadyExistsException:
            raise
        except Exception as e:
            logger.error(f"调度任务失败: {job_config.job_id}, 错误: {str(e)}")
            raise SchedulerExecutionException(
                job_id=job_config.job_id,
                error_message=f"调度任务失败: {str(e)}",
                original_error=e
            )

    async def get_job_status(self, job_id: JobId) -> Optional[Dict[str, Any]]:
        """获取任务状态
        
        Args:
            job_id: 任务ID
            
        Returns:
            任务状态信息，如果任务不存在则返回 None
        """
        try:
            status = await self._scheduler_port.get_job_status(job_id)
            return status
        except Exception as e:
            logger.error(f"获取任务状态失败: {job_id}, 错误: {str(e)}")
            raise SchedulerExecutionException(
                job_id=job_id,
                error_message=f"获取任务状态失败: {str(e)}",
                original_error=e
            )

    async def get_all_jobs_status(self) -> List[Dict[str, Any]]:
        """获取所有任务状态
        
        Returns:
            所有任务的状态信息列表
        """
        try:
            # 这里需要根据具体实现获取所有任务ID
            # 暂时返回空列表，实际实现中可能需要维护任务ID列表
            job_ids = await self._get_all_job_ids()
            
            statuses = []
            for job_id in job_ids:
                status = await self.get_job_status(job_id)
                if status:
                    statuses.append(status)
            
            return statuses
        except Exception as e:
            logger.error(f"获取所有任务状态失败: {str(e)}")
            raise SchedulerExecutionException(
                job_id=None,
                error_message=f"获取所有任务状态失败: {str(e)}",
                original_error=e
            )

    async def remove_job(self, job_id: JobId) -> None:
        """移除任务
        
        Args:
            job_id: 任务ID
            
        Raises:
            SchedulerJobNotFoundException: 任务不存在
        """
        try:
            await self._scheduler_port.remove_job(job_id)
            logger.info(f"任务移除成功: {job_id}")
                
        except SchedulerJobNotFoundException:
            raise
        except Exception as e:
            logger.error(f"移除任务失败: {job_id}, 错误: {str(e)}")
            raise SchedulerExecutionException(
                job_id=job_id,
                error_message=f"移除任务失败: {str(e)}",
                original_error=e
            )

    async def load_persisted_jobs(self, job_registry: JobRegistry) -> None:
        """从数据库加载持久化的任务配置
        
        Args:
            job_registry: 任务函数注册表
            
        读取所有启用的调度配置，匹配注册表中的任务函数，
        使用配置中的 cron 表达式注册到调度器。
        """
        try:
            logger.info("开始从数据库加载调度配置...")
            
            # 使用依赖注入的 Port 接口
            configs = await self._scheduler_job_config_repo_port.get_all_enabled()
            
            if not configs:
                logger.warning("数据库中没有启用的调度配置")
                return
            
            loaded_count = 0
            skipped_count = 0
            
            for config in configs:
                job_id = config.job_id
                
                # 检查注册表中是否有对应的任务函数
                if job_id not in job_registry:
                    logger.warning(
                        f"跳过调度配置 {job_id}：在任务注册表中未找到对应的任务函数"
                    )
                    skipped_count += 1
                    continue
                
                try:
                    # 调度任务
                    await self.schedule_job(config, job_registry)
                    loaded_count += 1
                    
                except SchedulerJobAlreadyExistsException:
                    logger.warning(f"任务已存在，跳过: {job_id}")
                    skipped_count += 1
                except Exception as e:
                    logger.error(f"加载任务配置失败: {job_id}, 错误: {str(e)}")
                    skipped_count += 1
            
            logger.info(
                f"调度配置加载完成：成功 {loaded_count} 个，跳过 {skipped_count} 个"
            )
            
        except Exception as e:
            # 数据库不可用或其他错误：记录错误但不阻止应用启动
            logger.error(
                f"从数据库加载调度配置失败，退化为手动注册模式: {e}",
                exc_info=True,
            )

    def _validate_job_config(self, job_config: JobConfigDTO) -> None:
        """验证任务配置
        
        Args:
            job_config: 任务配置
            
        Raises:
            SchedulerConfigurationException: 配置无效
        """
        # 基本字段验证
        if not job_config.job_id or not job_config.job_id.strip():
            raise SchedulerConfigurationException(
                config_key="job_id",
                config_value=job_config.job_id,
                reason="任务ID不能为空"
            )
        
        if not job_config.job_name or not job_config.job_name.strip():
            raise SchedulerConfigurationException(
                config_key="job_name",
                config_value=job_config.job_name,
                reason="任务名称不能为空"
            )
        
        if not job_config.cron_expression or not job_config.cron_expression.strip():
            raise SchedulerConfigurationException(
                config_key="cron_expression",
                config_value=job_config.cron_expression,
                reason="Cron表达式不能为空"
            )
        
        # 验证时区（简单验证）
        valid_timezones = ['UTC', 'Asia/Shanghai', 'Asia/Tokyo', 'America/New_York']
        if job_config.timezone not in valid_timezones:
            raise SchedulerConfigurationException(
                config_key="timezone",
                config_value=job_config.timezone,
                reason=f"不支持的时区: {job_config.timezone}"
            )
        
        # 验证 cron 表达式格式（应用层验证）
        parts = job_config.cron_expression.split()
        if len(parts) not in (5, 6):
            raise SchedulerConfigurationException(
                config_key="cron_expression",
                config_value=job_config.cron_expression,
                reason="Cron表达式必须包含 5 或 6 个部分"
            )
        
        # 简单验证每部分格式
        for part in parts:
            if part not in ('*', '?') and not all(c.isdigit() or c in '*/-' for c in part):
                raise SchedulerConfigurationException(
                    config_key="cron_expression",
                    config_value=job_config.cron_expression,
                    reason=f"无效的Cron表达式部分: {part}"
                )

    async def _get_all_job_ids(self) -> List[JobId]:
        """获取所有任务ID
        
        通过调度器端口获取所有任务并提取ID。
        
        Returns:
            任务ID列表
        """
        try:
            # 通过端口获取所有任务信息
            all_jobs = await self._scheduler_port.get_all_jobs()
            return [job["id"] for job in all_jobs if "id" in job]
        except Exception as e:
            logger.error(f"获取所有任务ID失败: {str(e)}")
            return []

    async def update_job_config(
        self,
        job_id: JobId,
        job_config: JobConfigDTO,
        job_registry: JobRegistry
    ) -> None:
        """更新任务配置
        
        Args:
            job_id: 任务ID
            job_config: 新的任务配置
            job_registry: 任务函数注册表
            
        Raises:
            SchedulerJobNotFoundException: 任务不存在
        """
        # 重新调度任务
        await self.schedule_job(job_config, job_registry)

    async def schedule_and_persist_job(
        self,
        job_config: JobConfigDTO,
        job_registry: JobRegistry
    ) -> None:
        """调度并持久化任务（原子编排）
        
        将任务调度和配置持久化封装为原子操作。
        如果持久化失败，回滚调度操作。
        
        Args:
            job_config: 任务配置
            job_registry: 任务函数注册表
            
        Raises:
            SchedulerJobNotFoundException: 任务函数未找到
            SchedulerExecutionException: 调度或持久化失败
        """
        try:
            # 先调度任务
            await self.schedule_job(job_config, job_registry)
            
            # 再持久化配置
            await self._scheduler_job_config_repo_port.upsert(job_config)
            
            logger.info(f"任务调度并持久化成功: {job_config.job_id}")
            
        except SchedulerJobNotFoundException:
            # 任务不在注册表中，直接传播异常
            raise
        except SchedulerJobAlreadyExistsException:
            # 任务已存在，直接传播异常
            raise
        except Exception as e:
            # 持久化失败时回滚调度
            logger.error(f"持久化任务配置失败，回滚调度操作: {job_config.job_id}")
            try:
                await self._scheduler_port.remove_job(job_config.job_id)
            except Exception as rollback_error:
                logger.error(f"回滚调度失败: {rollback_error}")
            
            raise SchedulerExecutionException(
                job_id=job_config.job_id,
                error_message=f"调度并持久化失败: {str(e)}",
                original_error=e
            )

    async def stop_and_disable_job(self, job_id: JobId) -> None:
        """停止并禁用任务
        
        从调度器移除任务，并将数据库配置标记为禁用。
        
        Args:
            job_id: 任务ID
        """
        try:
            # 移除调度任务
            await self._scheduler_port.remove_job(job_id)
            
            # 更新数据库配置为禁用
            await self._scheduler_job_config_repo_port.update_enabled(job_id, False)
            
            logger.info(f"任务已停止并禁用: {job_id}")
            
        except Exception as e:
            logger.error(f"停止并禁用任务失败: {job_id}, 错误: {str(e)}")
            raise SchedulerExecutionException(
                job_id=job_id,
                error_message=f"停止并禁用任务失败: {str(e)}",
                original_error=e
            )

    async def trigger_job(self, job_id: JobId, **kwargs) -> None:
        """手动触发任务执行
        
        立即触发指定任务的一次性执行，不影响其定时调度计划。
        
        Args:
            job_id: 任务ID
            **kwargs: 传递给任务函数的额外参数
            
        Raises:
            SchedulerJobNotFoundException: 任务不存在
        """
        try:
            await self._scheduler_port.trigger_job(job_id, **kwargs)
            logger.info(f"任务手动触发成功: {job_id}")
            
        except SchedulerJobNotFoundException:
            raise
        except Exception as e:
            logger.error(f"手动触发任务失败: {job_id}, 错误: {str(e)}")
            raise SchedulerExecutionException(
                job_id=job_id,
                error_message=f"手动触发任务失败: {str(e)}",
                original_error=e
            )

    async def query_execution_logs(
        self,
        job_id: Optional[JobId] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """查询任务执行历史
        
        通过注入的 Repository 查询任务执行日志。
        
        Args:
            job_id: 任务ID（可选），指定则查询该任务的日志，否则查询所有日志
            limit: 返回记录数限制
            
        Returns:
            执行日志列表
        """
        if self._scheduler_execution_log_repo_port is None:
            logger.warning("执行日志仓储未配置，返回空列表")
            return []
        
        try:
            if job_id:
                logs = await self._scheduler_execution_log_repo_port.get_by_job_id(
                    job_id, limit=limit
                )
            else:
                logs = await self._scheduler_execution_log_repo_port.get_recent(
                    limit=limit
                )
            
            return logs
            
        except Exception as e:
            logger.error(f"查询执行日志失败: {str(e)}")
            raise SchedulerExecutionException(
                job_id=job_id,
                error_message=f"查询执行日志失败: {str(e)}",
                original_error=e
            )
