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
