from fastapi import Request
from fastapi.responses import JSONResponse
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware

from src.shared.domain.exceptions import AppException
from src.shared.dtos import ErrorResponse


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    全局异常处理中间件
    捕获所有异常并返回统一的 JSON 格式错误响应
    """

    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except AppException as e:
            # 处理自定义应用异常
            logger.error(f"AppException: {e.message} | Path: {request.method} {request.url}")
            return JSONResponse(
                status_code=e.status_code,
                content=ErrorResponse(
                    success=False,
                    code=e.code,
                    message=e.message,
                ).model_dump(),
            )
        except Exception as e:
            # 处理所有未捕获的系统异常
            # 记录详细的栈信息，便于线上排查
            logger.exception(
                f"系统未处理异常: {str(e)} | "
                f"Method: {request.method} | "
                f"Path: {request.url.path} | "
                f"Client: {request.client.host if request.client else 'unknown'}"
            )
            return JSONResponse(
                status_code=500,
                content=ErrorResponse(
                    success=False,
                    code="INTERNAL_SERVER_ERROR",
                    message="服务器内部错误，请稍后重试",
                ).model_dump(),
            )
