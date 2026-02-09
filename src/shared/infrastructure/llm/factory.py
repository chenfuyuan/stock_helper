from src.shared.domain.ports.llm import ILLMProvider
from src.modules.llm_platform.application.services.llm_service import LLMService
from src.modules.llm_platform.infrastructure.registry import LLMRegistry

class LLMFactory:
    """
    LLM Factory (Proxy to LLMService)
    """
    @staticmethod
    def get_provider() -> ILLMProvider:
        # Return the Service which implements ILLMProvider
        # In a real DI container, we would get the singleton service
        # Here we instantiate it with the singleton registry
        return LLMService(registry=LLMRegistry())
