from typing import Any, Dict, Optional


class AppException(Exception):
    """
    应用基础异常类
    所有自定义异常应继承此类
    """

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class NotFoundException(AppException):
    """资源不存在异常 (404)"""

    def __init__(self, message: str = "Resource not found"):
        super().__init__(
            message=message,
            code="NOT_FOUND",
            status_code=404,
        )


class BadRequestException(AppException):
    """错误请求异常 (400)"""

    def __init__(self, message: str = "Bad request"):
        super().__init__(
            message=message,
            code="BAD_REQUEST",
            status_code=400,
        )


class UnauthorizedException(AppException):
    """未授权异常 (401)"""

    def __init__(self, message: str = "Unauthorized"):
        super().__init__(
            message=message,
            code="UNAUTHORIZED",
            status_code=401,
        )


class ForbiddenException(AppException):
    """禁止访问异常 (403)"""

    def __init__(self, message: str = "Forbidden"):
        super().__init__(
            message=message,
            code="FORBIDDEN",
            status_code=403,
        )

