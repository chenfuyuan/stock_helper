from typing import List, Optional
from loguru import logger
from src.modules.llm_platform.domain.entities.llm_config import LLMConfig
from src.modules.llm_platform.domain.ports.repositories.config_repo import ILLMConfigRepository
from src.modules.llm_platform.infrastructure.registry import LLMRegistry
from src.modules.llm_platform.domain.exceptions import ConfigNotFoundException, DuplicateConfigException

class ConfigService:
    """
    LLM 配置管理应用服务
    负责协调配置的增删改查以及通知注册表刷新。
    """
    def __init__(self, repo: ILLMConfigRepository, registry: LLMRegistry):
        self.repo = repo
        self.registry = registry

    async def get_all_configs(self) -> List[LLMConfig]:
        """
        获取所有 LLM 配置。
        """
        logger.debug("Fetching all LLM configs")
        configs = await self.repo.get_all()
        logger.debug(f"Retrieved {len(configs)} configs")
        return configs

    async def get_config(self, alias: str) -> LLMConfig:
        """
        获取指定别名的 LLM 配置。
        
        Args:
            alias (str): 配置别名
            
        Raises:
            ConfigNotFoundException: 当配置不存在时抛出
        """
        logger.debug(f"Fetching LLM config for alias: {alias}")
        config = await self.repo.get_by_alias(alias)
        if not config:
            logger.warning(f"Config not found: {alias}")
            raise ConfigNotFoundException(alias)
        return config

    async def create_config(self, config: LLMConfig) -> LLMConfig:
        """
        创建新的 LLM 配置。
        
        Args:
            config (LLMConfig): 配置实体
            
        Raises:
            DuplicateConfigException: 当别名已存在时抛出
        """
        logger.info(f"Creating new LLM config: {config.alias}")
        existing = await self.repo.get_by_alias(config.alias)
        if existing:
            logger.warning(f"Duplicate config alias attempted: {config.alias}")
            raise DuplicateConfigException(config.alias)
        
        saved = await self.repo.save(config)
        logger.info(f"Config created successfully: {saved.alias}, refreshing registry...")
        await self.registry.refresh() # Hot reload
        return saved

    async def update_config(self, alias: str, updates: dict) -> LLMConfig:
        """
        更新现有的 LLM 配置。
        
        Args:
            alias (str): 配置别名
            updates (dict): 更新的字段字典
            
        Raises:
            ConfigNotFoundException: 当配置不存在时抛出
        """
        logger.info(f"Updating LLM config: {alias} with updates: {updates.keys()}")
        existing = await self.repo.get_by_alias(alias)
        if not existing:
            logger.warning(f"Config not found for update: {alias}")
            raise ConfigNotFoundException(alias)
        
        # Apply updates
        for k, v in updates.items():
            if hasattr(existing, k) and v is not None:
                setattr(existing, k, v)
        
        saved = await self.repo.save(existing)
        logger.info(f"Config updated successfully: {alias}, refreshing registry...")
        await self.registry.refresh()
        return saved

    async def delete_config(self, alias: str):
        """
        删除 LLM 配置。
        
        Args:
            alias (str): 配置别名
            
        Raises:
            ConfigNotFoundException: 当配置不存在时抛出
        """
        logger.info(f"Deleting LLM config: {alias}")
        existing = await self.repo.get_by_alias(alias)
        if not existing:
            logger.warning(f"Config not found for deletion: {alias}")
            raise ConfigNotFoundException(alias)
        
        await self.repo.delete_by_alias(alias)
        logger.info(f"Config deleted successfully: {alias}, refreshing registry...")
        await self.registry.refresh()
        
    async def refresh_registry(self):
        """
        手动触发 LLM 注册表刷新。
        """
        logger.info("Manual registry refresh triggered")
        await self.registry.refresh()
