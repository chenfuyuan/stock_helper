"""数据同步服务基类。

封装所有数据同步服务共有的模板代码，包括：
- 异步 session 创建和管理
- ExecutionTracker 初始化和使用
- 统一的日志记录格式
"""

from abc import ABC, abstractmethod
from typing import Awaitable, Callable, TypeVar

from loguru import logger

from src.modules.foundation.infrastructure.execution_tracker import ExecutionTracker
from src.modules.foundation.infrastructure.persistence.repositories.scheduler_execution_log_repo import (
    SchedulerExecutionLogRepository,
)
from src.shared.infrastructure.db.session import AsyncSessionLocal

T = TypeVar("T")


class SyncServiceBase(ABC):
    """
    数据同步服务基类。

    所有数据同步服务（日线、财务、市场数据、基础数据）都应继承此类。
    子类只需实现具体的同步逻辑，公共的 session 管理、ExecutionTracker 集成
    由基类统一处理。

    Example:
        ```python
        class DailySyncService(SyncServiceBase):
            def _get_service_name(self) -> str:
                return "DailySyncService"

            async def run_incremental_sync(self, target_date: Optional[str]) -> dict:
                return await self._execute_with_tracking(
                    job_id="sync_daily_incremental",
                    operation=lambda: self._do_incremental_sync(target_date),
                    success_message="日线增量同步完成",
                )
        ```
    """

    def __init__(self) -> None:
        """
        初始化基类，绑定日志记录器。

        日志记录器会绑定服务名称，便于在日志中区分不同的同步服务。
        """
        self._logger = logger.bind(service=self._get_service_name())

    @abstractmethod
    def _get_service_name(self) -> str:
        """
        返回服务名称，用于日志和追踪。

        子类必须实现此方法，返回一个描述性的服务名称。

        Returns:
            服务名称，如 "DailySyncService"、"FinanceSyncService" 等
        """
        ...

    async def _execute_with_tracking(
        self,
        job_id: str,
        operation: Callable[[], Awaitable[T]],
        success_message: str,
    ) -> T:
        """
        在 ExecutionTracker 上下文中执行操作。

        这是核心的模板方法，封装了所有同步服务共有的模式：
        1. 创建异步 session
        2. 初始化 ExecutionTracker
        3. 记录开始日志
        4. 执行具体的同步操作
        5. 记录成功日志

        Args:
            job_id: 任务标识符，用于日志和追踪，如 "sync_daily_incremental"
            operation: 要执行的异步操作，通常是一个 lambda 或内部方法
            success_message: 操作成功完成时记录的日志消息

        Returns:
            operation 的返回值，通常是同步结果对象或字典

        Raises:
            原样传播 operation 中抛出的任何异常，ExecutionTracker 会捕获并记录

        Example:
            ```python
            return await self._execute_with_tracking(
                job_id="sync_daily_incremental",
                operation=lambda: self._do_incremental_sync(target_date),
                success_message=f"日线增量同步完成，日期: {target_date}",
            )
            ```
        """
        async with AsyncSessionLocal() as session:
            repo = SchedulerExecutionLogRepository(session)
            async with ExecutionTracker(job_id=job_id, repo=repo):
                self._logger.info(f"开始执行: {job_id}")
                result = await operation()
                self._logger.info(success_message)
                return result
