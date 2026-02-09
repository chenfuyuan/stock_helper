from src.shared.domain.exceptions import AppException

class ConfigNotFoundException(AppException):
    def __init__(self, alias: str):
        super().__init__(
            message=f"LLM Config with alias '{alias}' not found",
            code="LLM_CONFIG_NOT_FOUND",
            status_code=404
        )

class DuplicateConfigException(AppException):
    def __init__(self, alias: str):
        super().__init__(
            message=f"LLM Config with alias '{alias}' already exists",
            code="LLM_CONFIG_DUPLICATE",
            status_code=409
        )

class LLMProviderException(AppException):
    def __init__(self, message: str):
        super().__init__(
            message=message,
            code="LLM_PROVIDER_ERROR",
            status_code=500
        )
