from typing import Optional, List
from src.shared.domain.ports.llm import ILLMProvider
from src.modules.llm_platform.infrastructure.router import LLMRouter
from src.modules.llm_platform.infrastructure.registry import LLMRegistry

class LLMService(ILLMProvider):
    """
    LLM Platform Facade Service
    Exposes LLM capabilities to other modules.
    """
    def __init__(self, registry: LLMRegistry = None):
        self.registry = registry or LLMRegistry()
        self.router = LLMRouter(self.registry)

    async def generate(
        self, 
        prompt: str, 
        system_message: Optional[str] = None, 
        temperature: float = 0.7,
        alias: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> str:
        """
        Generate text using LLM.
        Supports routing by alias or tags.
        """
        return await self.router.generate(
            prompt, 
            system_message, 
            temperature, 
            alias=alias, 
            tags=tags
        )
