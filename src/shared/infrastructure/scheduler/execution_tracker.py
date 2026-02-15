"""调度执行跟踪器"""

import logging
import uuid
from datetime import datetime
from typing import Optional, Callable, Any
from contextlib import asynccontextmanager

from .repositories.scheduler_execution_log_repo import SchedulerExecutionLogRepository

logger = logging.getLogger(__name__)


class ExecutionTracker:
    """调度执行跟踪器（异步上下文管理器）
    
    用于包裹 job 函数的执行，自动记录执行日志到数据库。
    进入时创建 RUNNING 状态的日志记录，正常退出更新为 SUCCESS，
    异常退出更新为 FAILED。自身的 DB 写入失败不会中断 job 执行。
    
    使用示例：
        async with ExecutionTracker(job_id="sync_daily", repo=repo):
            await actual_job_function()
    """

    def __init__(
        self,
        job_id: str,
        repo: SchedulerExecutionLogRepository,
    ):
        """初始化执行跟踪器
        
        Args:
            job_id: 任务标识
            repo: 执行日志仓储
        """
        self._job_id = job_id
        self._repo = repo
        self._log_id: Optional[uuid.UUID] = None
        self._started_at: Optional[datetime] = None

    async def __aenter__(self) -> "ExecutionTracker":
        """进入上下文：创建 RUNNING 状态的执行日志"""
        self._started_at = datetime.utcnow()
        
        try:
            log = await self._repo.create(
                job_id=self._job_id,
                started_at=self._started_at,
                status="RUNNING",
            )
            self._log_id = log.id
            logger.info(f"调度任务 {self._job_id} 开始执行，日志 ID: {self._log_id}")
        except Exception as e:
            # DB 写入失败不中断 job 执行，仅记录错误日志
            logger.error(
                f"创建调度执行日志失败 (job_id={self._job_id}): {e}",
                exc_info=True,
            )
            self._log_id = None
        
        return self

    async def __aexit__(
        self,
        exc_type: Optional[type],
        exc_val: Optional[BaseException],
        exc_tb: Optional[Any],
    ) -> bool:
        """退出上下文：更新执行日志状态
        
        正常退出时更新为 SUCCESS，异常退出时更新为 FAILED。
        
        Returns:
            False（不抑制异常，让异常继续向上传播）
        """
        if self._log_id is None:
            # 进入时创建日志失败，跳过更新
            return False
        
        finished_at = datetime.utcnow()
        duration_ms = int((finished_at - self._started_at).total_seconds() * 1000)
        
        if exc_type is None:
            # 正常退出：SUCCESS
            status = "SUCCESS"
            error_message = None
            logger.info(
                f"调度任务 {self._job_id} 执行成功，耗时 {duration_ms}ms"
            )
        else:
            # 异常退出：FAILED
            status = "FAILED"
            error_message = f"{exc_type.__name__}: {str(exc_val)}"
            logger.error(
                f"调度任务 {self._job_id} 执行失败: {error_message}，耗时 {duration_ms}ms"
            )
        
        try:
            await self._repo.update(
                log_id=self._log_id,
                status=status,
                finished_at=finished_at,
                error_message=error_message,
                duration_ms=duration_ms,
            )
        except Exception as e:
            # DB 写入失败不中断 job 执行，仅记录错误日志
            logger.error(
                f"更新调度执行日志失败 (job_id={self._job_id}, log_id={self._log_id}): {e}",
                exc_info=True,
            )
        
        # 不抑制异常，让异常继续向上传播
        return False
