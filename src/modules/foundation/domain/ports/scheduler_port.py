"""调度器领域端口接口

定义调度器能力的抽象契约，建立依赖倒置基础。
所有调度器相关的操作都通过此接口进行，隐藏具体实现细节。
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Callable, List


class SchedulerPort(ABC):
    """调度器端口接口
    
    定义调度器的核心能力，包括任务调度、生命周期管理和状态查询。
    实现类必须封装具体的调度器框架（如 APScheduler）细节。
    """

    @abstractmethod
    async def schedule_job(
        self,
        job_id: str,
        job_func: Callable,
        cron_expression: str,
        timezone: str = "UTC",
        **kwargs
    ) -> None:
        """调度定时任务
        
        Args:
            job_id: 任务唯一标识符
            job_func: 要执行的异步任务函数
            cron_expression: Cron 表达式，定义执行时间
            timezone: 时区，默认为 UTC
            **kwargs: 传递给任务函数的额外参数
        """
        pass

    @abstractmethod
    async def start_scheduler(self) -> None:
        """启动调度器
        
        启动调度器的后台任务循环，开始执行已调度的任务。
        如果调度器已经在运行，应该忽略此调用。
        """
        pass

    @abstractmethod
    async def shutdown_scheduler(self) -> None:
        """关闭调度器
        
        优雅关闭调度器，停止所有正在运行的任务和后台循环。
        等待当前执行的任务完成后再关闭。
        """
        pass

    @abstractmethod
    async def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态
        
        Args:
            job_id: 任务唯一标识符
            
        Returns:
            任务状态信息字典，包含下次执行时间、触发器等信息
            如果任务不存在则返回 None
        """
        pass

    @abstractmethod
    async def get_all_jobs(self) -> List[Dict[str, Any]]:
        """获取所有任务信息
        
        Returns:
            所有任务的信息列表，每个任务包含 id、name、next_run_time 等信息
        """
        pass

    @abstractmethod
    async def remove_job(self, job_id: str) -> None:
        """移除已调度的任务
        
        从调度器中移除指定的任务。如果任务正在执行，等待其完成后移除。
        如果任务不存在，不抛出异常（幂等操作）。
        
        Args:
            job_id: 任务唯一标识符
        """
        pass

    @abstractmethod
    async def trigger_job(self, job_id: str, **kwargs) -> None:
        """立即触发一次任务执行
        
        手动触发指定任务的一次性执行，不影响其定时调度计划。
        
        Args:
            job_id: 任务唯一标识符
            **kwargs: 传递给任务函数的额外参数
            
        Raises:
            SchedulerJobNotFoundException: 如果任务不存在
        """
        pass
