"""Research 模块领域异常。"""
from src.shared.domain.exceptions import AppException


class LLMOutputParseError(AppException):
    """LLM 返回内容无法解析为技术分析结果（非 JSON 或缺少必填字段）时抛出。"""

    def __init__(self, message: str = "LLM 返回内容无法解析为技术分析结果", details: dict | None = None):
        super().__init__(
            message=message,
            code="LLM_OUTPUT_PARSE_ERROR",
            status_code=422,
            details=details or {},
        )
