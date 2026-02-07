from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from loguru import logger

from app.core.exceptions import AppException

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
            logger.error(f"AppException: {e.message}")
            return JSONResponse(
                status_code=e.status_code,
                content={
                    "success": False,
                    "code": e.code,
                    "message": e.message,
                    "details": e.details
                }
            )
        except Exception as e:
            # 处理未捕获的系统异常
            logger.exception(f"Unhandled exception: {str(e)}")
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "Internal server error",
                }
            )
