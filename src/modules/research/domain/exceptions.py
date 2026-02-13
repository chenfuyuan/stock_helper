"""Research 模块领域异常。"""
from src.shared.domain.exceptions import AppException, BadRequestException


class LLMOutputParseError(AppException):
    """LLM 返回内容无法解析为技术分析结果（非 JSON 或缺少必填字段）时抛出。"""

    def __init__(self, message: str = "LLM 返回内容无法解析为技术分析结果", details: dict | None = None):
        super().__init__(
            message=message,
            code="LLM_OUTPUT_PARSE_ERROR",
            status_code=422,
            details=details or {},
        )


class StockNotFoundError(AppException):
    """请求的股票代码不存在。"""

    def __init__(self, symbol: str):
        super().__init__(
            message=f"该标的不存在: {symbol}",
            code="STOCK_NOT_FOUND",
            status_code=404,
            details={"symbol": symbol},
        )


class CatalystSearchError(BadRequestException):
    """催化剂搜索全部失败时抛出。"""

    def __init__(self, message: str = "催化剂搜索全部失败"):
        super().__init__(message=message)
