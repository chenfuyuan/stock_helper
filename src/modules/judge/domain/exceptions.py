"""
Judge 领域异常。

所有异常继承 shared 的 AppException，便于 Presentation 层统一映射 HTTP 状态码。
"""

from src.shared.domain.exceptions import AppException


class LLMOutputParseError(AppException):
    """LLM 输出解析失败（非法 JSON 或字段不符合契约）。"""

    def __init__(self, message: str = "LLM 输出解析失败", details: dict | None = None):
        super().__init__(
            message=message,
            code="LLM_OUTPUT_PARSE_ERROR",
            status_code=500,
            details=details or {},
        )
