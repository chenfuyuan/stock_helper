from typing import Dict, Optional, List
from loguru import logger
import asyncio

from src.shared.domain.ports.llm import ILLMProvider
from src.modules.llm_platform.infrastructure.adapters.openai import OpenAIProvider
from src.modules.llm_platform.domain.entities.llm_config import LLMConfig
from src.modules.llm_platform.domain.ports.repositories.config_repo import ILLMConfigRepository
from src.shared.config import settings

class LLMRegistry:
    _instance = None
    _providers: Dict[str, ILLMProvider] = {}
    _configs: Dict[str, LLMConfig] = {}
    _repo: Optional[ILLMConfigRepository] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LLMRegistry, cls).__new__(cls)
        return cls._instance

    def set_repository(self, repo: ILLMConfigRepository):
        self._repo = repo

    async def refresh(self):
        """Reload configs from DB"""
        if not self._repo:
            logger.warning("Repository not set for LLMRegistry, cannot refresh from DB")
            return

        try:
            configs = await self._repo.get_active_configs()
            
            # Clear and rebuild
            self._providers.clear()
            self._configs.clear()
            
            for config in configs:
                self._register(config)
                
            logger.info(f"LLM Registry refreshed. Loaded {len(self._providers)} providers.")
        except Exception as e:
            logger.error(f"Failed to refresh LLM Registry: {str(e)}")

    def _register(self, config: LLMConfig):
        try:
            if config.provider_type.lower() == "openai":
                provider = OpenAIProvider(
                    api_key=config.api_key,
                    base_url=config.base_url,
                    model=config.model_name
                )
            else:
                logger.warning(f"Unsupported provider type: {config.provider_type}")
                return

            self._providers[config.alias] = provider
            self._configs[config.alias] = config
        except Exception as e:
            logger.error(f"Failed to register LLM provider {config.alias}: {str(e)}")

    def get_provider(self, alias: str) -> Optional[ILLMProvider]:
        return self._providers.get(alias)

    def get_all_configs(self) -> List[LLMConfig]:
        return list(self._configs.values())
