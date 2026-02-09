from abc import ABC, abstractmethod
from typing import List, Optional
from src.modules.llm_platform.domain.entities.llm_config import LLMConfig

class ILLMConfigRepository(ABC):
    @abstractmethod
    async def get_all(self) -> List[LLMConfig]:
        """获取所有配置"""
        pass

    @abstractmethod
    async def get_active_configs(self) -> List[LLMConfig]:
        """获取所有已激活的配置"""
        pass

    @abstractmethod
    async def get_by_alias(self, alias: str) -> Optional[LLMConfig]:
        """根据别名获取配置"""
        pass

    @abstractmethod
    async def save(self, config: LLMConfig) -> LLMConfig:
        """保存配置 (新增或更新)"""
        pass

    @abstractmethod
    async def delete_by_alias(self, alias: str) -> bool:
        """根据别名删除配置"""
        pass
