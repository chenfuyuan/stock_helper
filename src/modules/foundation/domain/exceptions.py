"""Foundation 模块领域异常

Scheduler 相关异常定义，从 shared 迁移到 Foundation Bounded Context。
所有异常继承自 src.shared.domain.exceptions.AppException，保持全局异常处理中间件的兼容性。
"""

from typing import Any, Dict, Optional

from src.shared.domain.exceptions import AppException


class SchedulerException(AppException):
    """调度器基础异常类"""
    
    def __init__(
        self,
        message: str,
        code: str = "SCHEDULER_ERROR",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            code=code,
            status_code=status_code,
            details=details,
        )


class SchedulerJobNotFoundException(SchedulerException):
    """调度任务未找到异常"""
    
    def __init__(self, job_id: str):
        self.job_id = job_id
        message = f"调度任务未找到: {job_id}"
        super().__init__(
            message=message,
            code="SCHEDULER_JOB_NOT_FOUND",
            status_code=404,
        )


class SchedulerJobAlreadyExistsException(SchedulerException):
    """调度任务已存在异常"""
    
    def __init__(self, job_id: str):
        self.job_id = job_id
        message = f"调度任务已存在: {job_id}"
        super().__init__(
            message=message,
            code="SCHEDULER_JOB_ALREADY_EXISTS",
            status_code=409,
        )


class SchedulerConfigurationException(SchedulerException):
    """调度器配置异常"""
    
    def __init__(
        self,
        config_key: str,
        config_value: Any,
        reason: str
    ):
        self.config_key = config_key
        self.config_value = config_value
        self.reason = reason
        message = f"调度器配置错误: {config_key}={config_value}, 原因: {reason}"
        super().__init__(
            message=message,
            code="SCHEDULER_CONFIG_ERROR",
            status_code=400,
        )


class SchedulerExecutionException(SchedulerException):
    """调度器执行异常"""
    
    def __init__(
        self,
        job_id: Optional[str],
        error_message: str,
        original_error: Optional[Exception] = None
    ):
        self.job_id = job_id
        self.error_message = error_message
        self.original_error = original_error
        message = f"调度器执行错误: {job_id}, 错误: {error_message}"
        super().__init__(
            message=message,
            code="SCHEDULER_EXECUTION_ERROR",
            status_code=500,
        )
