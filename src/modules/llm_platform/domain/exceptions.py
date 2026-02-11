from src.shared.domain.exceptions import AppException


class ConfigNotFoundException(AppException):
    def __init__(self, alias: str):
        super().__init__(
            message=f"LLM Config with alias '{alias}' not found",
            code="LLM_CONFIG_NOT_FOUND",
            status_code=404,
        )


class DuplicateConfigException(AppException):
    def __init__(self, alias: str):
        super().__init__(
            message=f"LLM Config with alias '{alias}' already exists",
            code="LLM_CONFIG_DUPLICATE",
            status_code=409,
        )


class LLMProviderException(AppException):
    def __init__(self, message: str):
        super().__init__(
            message=message,
            code="LLM_PROVIDER_ERROR",
            status_code=500,
        )


class LLMConnectionError(AppException):
    """LLM connection or invocation error (503)."""

    def __init__(self, message: str = "LLM Service Unavailable"):
        super().__init__(
            message=message,
            code="LLM_SERVICE_ERROR",
            status_code=503,
        )


class ModelConfigurationError(AppException):
    """Model configuration error (500)."""

    def __init__(self, message: str = "Invalid model configuration"):
        super().__init__(
            message=message,
            code="MODEL_CONFIG_ERROR",
            status_code=500,
        )


class NoAvailableModelError(AppException):
    """No available LLM model error (503)."""

    def __init__(self, message: str = "No available LLM models found"):
        super().__init__(
            message=message,
            code="NO_AVAILABLE_MODEL",
            status_code=503,
        )
