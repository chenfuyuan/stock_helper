from apscheduler.schedulers.asyncio import AsyncIOScheduler
from loguru import logger

class SchedulerService:
    """
    调度器服务
    封装 APScheduler
    """
    _scheduler: AsyncIOScheduler = None

    @classmethod
    def get_scheduler(cls) -> AsyncIOScheduler:
        if cls._scheduler is None:
            cls._scheduler = AsyncIOScheduler()
        return cls._scheduler

    @classmethod
    def start(cls):
        """启动调度器"""
        scheduler = cls.get_scheduler()
        if not scheduler.running:
            logger.info("Starting APScheduler...")
            scheduler.start()

    @classmethod
    def shutdown(cls):
        """关闭调度器"""
        if cls._scheduler and cls._scheduler.running:
            logger.info("Shutting down APScheduler...")
            cls._scheduler.shutdown()
