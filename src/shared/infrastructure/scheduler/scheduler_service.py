"""调度器服务"""

import logging
from typing import Dict, Callable, Any
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from .repositories.scheduler_job_config_repo import SchedulerJobConfigRepository

logger = logging.getLogger(__name__)


class SchedulerService:
    """任务调度器服务（Singleton）
    
    封装 APScheduler (AsyncIOScheduler)，提供全局统一的定时任务管理能力。
    负责任务的启动、停止、管理，以及从数据库加载持久化配置。
    """

    _scheduler: AsyncIOScheduler = None

    @classmethod
    def get_scheduler(cls) -> AsyncIOScheduler:
        """获取调度器单例
        
        如果尚未初始化，则创建一个新的 AsyncIOScheduler 实例。

        Returns:
            全局调度器实例
        """
        if cls._scheduler is None:
            logger.debug("初始化新的 AsyncIOScheduler 实例")
            cls._scheduler = AsyncIOScheduler()
        return cls._scheduler

    @classmethod
    def start(cls):
        """启动调度器
        
        如果调度器未运行，则启动它。
        """
        scheduler = cls.get_scheduler()
        if not scheduler.running:
            logger.info("启动 APScheduler...")
            try:
                scheduler.start()
                logger.info("APScheduler 启动成功")
            except Exception as e:
                logger.error(f"启动 APScheduler 失败: {str(e)}")
                raise e
        else:
            logger.debug("APScheduler 已在运行中")

    @classmethod
    def shutdown(cls):
        """优雅关闭调度器
        
        停止所有正在运行的任务和调度循环。
        """
        if cls._scheduler and cls._scheduler.running:
            logger.info("关闭 APScheduler...")
            try:
                cls._scheduler.shutdown()
                logger.info("APScheduler 关闭成功")
            except Exception as e:
                logger.error(f"关闭 APScheduler 失败: {str(e)}")
        else:
            logger.debug("APScheduler 未运行或已关闭")

    @classmethod
    async def load_persisted_jobs(
        cls,
        registry: Dict[str, Callable],
        session_factory: Callable,
    ) -> None:
        """从数据库加载持久化的调度配置并注册到 APScheduler
        
        读取所有 enabled=True 的调度配置，匹配 registry 中的 job 函数，
        使用配置中的 cron 表达式注册到 APScheduler。
        
        数据库不可用时会记录错误日志但不阻止应用启动（退化为手动注册模式）。
        
        Args:
            registry: job_id -> job_function 的映射表
            session_factory: 数据库会话工厂函数
        """
        try:
            logger.info("开始从数据库加载调度配置...")
            
            # 创建数据库会话
            async with session_factory() as session:
                repo = SchedulerJobConfigRepository(session)
                configs = await repo.get_all_enabled()
            
            if not configs:
                logger.warning("数据库中没有启用的调度配置")
                return
            
            scheduler = cls.get_scheduler()
            loaded_count = 0
            skipped_count = 0
            
            for config in configs:
                job_id = config.job_id
                
                # 检查 registry 中是否有对应的 job 函数
                if job_id not in registry:
                    logger.warning(
                        f"跳过调度配置 {job_id}：在 JOB_REGISTRY 中未找到对应的 job 函数"
                    )
                    skipped_count += 1
                    continue
                
                job_func = registry[job_id]
                
                # 使用配置中的 cron 表达式创建触发器
                trigger = CronTrigger.from_crontab(
                    config.cron_expression,
                    timezone=config.timezone,
                )
                
                # 注册到 APScheduler
                scheduler.add_job(
                    job_func,
                    trigger=trigger,
                    id=job_id,
                    name=config.job_name,
                    replace_existing=True,
                    kwargs=config.job_kwargs or {},
                )
                
                logger.info(
                    f"已加载调度配置: {job_id} ({config.job_name}) - "
                    f"cron={config.cron_expression}, timezone={config.timezone}"
                )
                loaded_count += 1
            
            logger.info(
                f"调度配置加载完成：成功 {loaded_count} 个，跳过 {skipped_count} 个"
            )
            
        except Exception as e:
            # 数据库不可用或其他错误：记录错误但不阻止应用启动
            logger.error(
                f"从数据库加载调度配置失败，退化为手动注册模式: {e}",
                exc_info=True,
            )
