"""
Coordinator 领域异常。

继承 src.shared.domain.exceptions.AppException，便于 Presentation 层映射 HTTP 状态码。
"""
from src.shared.domain.exceptions import AppException


class AllExpertsFailedError(AppException):
    """全部专家执行失败时抛出。"""

    def __init__(self, message: str = "全部专家执行失败"):
        super().__init__(
            message=message,
            code="ALL_EXPERTS_FAILED",
            status_code=500,
        )


class SessionNotFoundError(AppException):
    """指定的研究会话不存在时抛出。"""

    def __init__(self, message: str = "研究会话不存在"):
        super().__init__(
            message=message,
            code="SESSION_NOT_FOUND",
            status_code=404,
        )


class SessionNotRetryableError(AppException):
    """研究会话当前状态不允许重试时抛出（如 completed 或 running）。"""

    def __init__(self, message: str = "该研究会话当前状态不允许重试", status_code: int = 400):
        super().__init__(
            message=message,
            code="SESSION_NOT_RETRYABLE",
            status_code=status_code,
        )
