from typing import List, Optional
from src.modules.llm_platform.domain.entities.llm_config import LLMConfig
from src.modules.llm_platform.domain.ports.repositories.config_repo import ILLMConfigRepository
from src.modules.llm_platform.infrastructure.registry import LLMRegistry
from src.modules.llm_platform.domain.exceptions import ConfigNotFoundException, DuplicateConfigException

class ConfigService:
    def __init__(self, repo: ILLMConfigRepository, registry: LLMRegistry):
        self.repo = repo
        self.registry = registry

    async def get_all_configs(self) -> List[LLMConfig]:
        return await self.repo.get_all()

    async def get_config(self, alias: str) -> LLMConfig:
        config = await self.repo.get_by_alias(alias)
        if not config:
            raise ConfigNotFoundException(alias)
        return config

    async def create_config(self, config: LLMConfig) -> LLMConfig:
        existing = await self.repo.get_by_alias(config.alias)
        if existing:
            raise DuplicateConfigException(config.alias)
        
        saved = await self.repo.save(config)
        await self.registry.refresh() # Hot reload
        return saved

    async def update_config(self, alias: str, updates: dict) -> LLMConfig:
        existing = await self.repo.get_by_alias(alias)
        if not existing:
            raise ConfigNotFoundException(alias)
        
        # Apply updates
        for k, v in updates.items():
            if hasattr(existing, k) and v is not None:
                setattr(existing, k, v)
        
        saved = await self.repo.save(existing)
        await self.registry.refresh()
        return saved

    async def delete_config(self, alias: str):
        existing = await self.repo.get_by_alias(alias)
        if not existing:
            raise ConfigNotFoundException(alias)
        
        await self.repo.delete_by_alias(alias)
        await self.registry.refresh()
        
    async def refresh_registry(self):
        await self.registry.refresh()
