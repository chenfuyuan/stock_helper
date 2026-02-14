from apscheduler.schedulers.asyncio import AsyncIOScheduler
from loguru import logger


class SchedulerService:
    """
    任务调度器服务 (Singleton)

    封装 APScheduler (AsyncIOScheduler)，提供全局统一的定时任务管理能力。
    负责任务的启动、停止和管理。
    """

    _scheduler: AsyncIOScheduler = None

    @classmethod
    def get_scheduler(cls) -> AsyncIOScheduler:
        """
        获取调度器单例。
        如果尚未初始化，则创建一个新的 AsyncIOScheduler 实例。

        Returns:
            AsyncIOScheduler: 全局调度器实例。
        """
        if cls._scheduler is None:
            logger.debug("Initializing new AsyncIOScheduler instance")
            cls._scheduler = AsyncIOScheduler()
        return cls._scheduler

    @classmethod
    def start(cls):
        """
        启动调度器。
        如果调度器未运行，则启动它。
        """
        scheduler = cls.get_scheduler()
        if not scheduler.running:
            logger.info("Starting APScheduler...")
            try:
                scheduler.start()
                logger.info("APScheduler started successfully")
            except Exception as e:
                logger.error(f"Failed to start APScheduler: {str(e)}")
                raise e
        else:
            logger.debug("APScheduler is already running")

    @classmethod
    def shutdown(cls):
        """
        优雅关闭调度器。
        停止所有正在运行的任务和调度循环。
        """
        if cls._scheduler and cls._scheduler.running:
            logger.info("Shutting down APScheduler...")
            try:
                cls._scheduler.shutdown()
                logger.info("APScheduler shutdown successfully")
            except Exception as e:
                logger.error(f"Failed to shutdown APScheduler: {str(e)}")
        else:
            logger.debug("APScheduler is not running or already shutdown")
