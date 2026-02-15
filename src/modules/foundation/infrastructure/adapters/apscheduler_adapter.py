"""APScheduler 基础设施适配器

实现 SchedulerPort 接口，封装 APScheduler 的具体操作。
仅负责调度器的基础操作，不涉及数据访问逻辑。
"""

from datetime import datetime
from typing import Dict, Any, Optional, Callable, List
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from loguru import logger

from src.modules.foundation.domain.ports.scheduler_port import SchedulerPort
from src.modules.foundation.domain.exceptions import (
    SchedulerException,
    SchedulerJobNotFoundException,
    SchedulerJobAlreadyExistsException,
    SchedulerExecutionException
)
from src.modules.foundation.domain.types import JobId, JobFunction


class APSchedulerAdapter(SchedulerPort):
    """APScheduler 适配器
    
    实现 SchedulerPort 接口，封装 APScheduler 的具体操作。
    负责调度器的启动、停止、任务管理等基础功能。
    """

    def __init__(self):
        """初始化 APScheduler 适配器"""
        self._scheduler = AsyncIOScheduler()
        self._is_initialized = False

    async def schedule_job(
        self,
        job_id: str,
        job_func: JobFunction,
        cron_expression: str,
        timezone: str = "UTC",
        **kwargs
    ) -> None:
        """调度定时任务
        
        Args:
            job_id: 任务唯一标识符
            job_func: 要执行的异步任务函数
            cron_expression: Cron 表达式
            timezone: 时区
            **kwargs: 传递给任务函数的额外参数
            
        Raises:
            SchedulerJobAlreadyExistsException: 任务已存在
            SchedulerExecutionException: 调度失败
        """
        try:
            # 检查任务是否已存在
            if self._scheduler.get_job(job_id):
                raise SchedulerJobAlreadyExistsException(job_id)
            
            # 创建 Cron 触发器
            trigger = CronTrigger.from_crontab(cron_expression, timezone=timezone)
            
            # 添加任务到调度器
            self._scheduler.add_job(
                job_func,
                trigger=trigger,
                id=job_id,
                name=job_id,
                replace_existing=False,
                kwargs=kwargs
            )
            
            logger.info(f"任务调度成功: {job_id}, cron={cron_expression}, timezone={timezone}")
            
        except SchedulerJobAlreadyExistsException:
            raise
        except Exception as e:
            logger.error(f"调度任务失败: {job_id}, 错误: {str(e)}")
            raise SchedulerExecutionException(
                job_id=job_id,
                error_message=f"调度任务失败: {str(e)}",
                original_error=e
            )

    async def start_scheduler(self) -> None:
        """启动调度器
        
        启动调度器的后台任务循环。
        如果调度器已经在运行，则忽略此调用。
        
        Raises:
            SchedulerException: 启动失败
        """
        try:
            if not self._is_initialized:
                # APScheduler 不需要手动配置实例
                self._is_initialized = True
            
            if not self._scheduler.running:
                self._scheduler.start()
                logger.info("APScheduler 启动成功")
            else:
                logger.debug("APScheduler 已在运行中")
                
        except Exception as e:
            logger.error(f"启动 APScheduler 失败: {str(e)}")
            raise SchedulerException(
                message=f"启动调度器失败: {str(e)}",
                code="SCHEDULER_START_FAILED"
            )

    async def shutdown_scheduler(self) -> None:
        """关闭调度器
        
        优雅关闭调度器，停止所有正在运行的任务。
        """
        try:
            if self._scheduler and self._scheduler.running:
                self._scheduler.shutdown(wait=True)
                logger.info("APScheduler 关闭成功")
            else:
                logger.debug("APScheduler 未运行或已关闭")
                
        except Exception as e:
            logger.error(f"关闭 APScheduler 失败: {str(e)}")
            raise SchedulerException(
                message=f"关闭调度器失败: {str(e)}",
                code="SCHEDULER_SHUTDOWN_FAILED"
            )

    async def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态
        
        Args:
            job_id: 任务唯一标识符
            
        Returns:
            任务状态信息字典，如果任务不存在则返回 None
        """
        try:
            job = self._scheduler.get_job(job_id)
            if job is None:
                return None
            
            return {
                "id": job.id,
                "job_name": job.name,
                "is_running": True,  # APScheduler 中的任务默认为运行状态
                "next_run_time": job.next_run_time,
                "trigger": str(job.trigger),
                "kwargs": job.kwargs,
                "misfire_grace_time": getattr(job, 'misfire_grace_time', None),
                "max_instances": getattr(job, 'max_instances', None)
            }
            
        except Exception as e:
            logger.error(f"获取任务状态失败: {job_id}, 错误: {str(e)}")
            raise SchedulerExecutionException(
                job_id=job_id,
                error_message=f"获取任务状态失败: {str(e)}",
                original_error=e
            )

    async def remove_job(self, job_id: str) -> None:
        """移除任务
        
        Args:
            job_id: 任务唯一标识符
            
        Raises:
            SchedulerJobNotFoundException: 任务不存在
            SchedulerExecutionException: 移除失败
        """
        try:
            job = self._scheduler.get_job(job_id)
            if job is None:
                raise SchedulerJobNotFoundException(job_id)
            
            self._scheduler.remove_job(job_id)
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

    async def trigger_job(self, job_id: str, **kwargs) -> None:
        """立即触发任务
        
        Args:
            job_id: 任务唯一标识符
            **kwargs: 传递给任务函数的额外参数
            
        Raises:
            SchedulerJobNotFoundException: 任务不存在
            SchedulerExecutionException: 触发失败
        """
        try:
            job = self._scheduler.get_job(job_id)
            if job is None:
                raise SchedulerJobNotFoundException(job_id)
            
            # 获取调度时的参数，合并手动触发的参数
            job_kwargs = job.kwargs.copy()
            job_kwargs.update(kwargs)
            
            # 创建立即执行的触发器
            trigger = DateTrigger(run_date=datetime.now())
            
            # 生成临时任务ID以避免冲突
            temp_job_id = f"{job_id}_manual_{datetime.now().timestamp()}"
            
            self._scheduler.add_job(
                job.func,
                trigger=trigger,
                id=temp_job_id,
                name=f"Manual trigger for {job_id}",
                kwargs=job_kwargs
            )
            
            logger.info(f"任务触发成功: {job_id} (临时ID: {temp_job_id})")
            
        except SchedulerJobNotFoundException:
            raise
        except Exception as e:
            logger.error(f"触发任务失败: {job_id}, 错误: {str(e)}")
            raise SchedulerExecutionException(
                job_id=job_id,
                error_message=f"触发任务失败: {str(e)}",
                original_error=e
            )

    async def get_all_jobs(self) -> List[Dict[str, Any]]:
        """获取所有任务信息
        
        Returns:
            任务信息列表
        """
        try:
            jobs = []
            for job in self._scheduler.get_jobs():
                jobs.append({
                    "id": job.id,
                    "name": job.name,
                    "next_run_time": job.next_run_time,
                    "trigger": str(job.trigger),
                    "kwargs": job.kwargs
                })
            
            return jobs
            
        except Exception as e:
            logger.error(f"获取所有任务失败: {str(e)}")
            return [{"error": str(e)}]
