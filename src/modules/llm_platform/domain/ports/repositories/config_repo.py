from abc import ABC, abstractmethod
from typing import List, Optional

from src.modules.llm_platform.domain.entities.llm_config import LLMConfig


class ILLMConfigRepository(ABC):
    """
    LLM 配置仓储接口 (Port)
    定义了对 LLM 配置数据的持久化操作规范。
    """

    @abstractmethod
    async def get_all(self) -> List[LLMConfig]:
        """
        获取数据库中所有的 LLM 配置。

        Returns:
            List[LLMConfig]: 配置列表。
        """

    @abstractmethod
    async def get_active_configs(self) -> List[LLMConfig]:
        """
        获取所有状态为“激活”的 LLM 配置。

        Returns:
            List[LLMConfig]: 已激活的配置列表。
        """

    @abstractmethod
    async def get_by_alias(self, alias: str) -> Optional[LLMConfig]:
        """
        根据别名查找特定的 LLM 配置。

        Args:
            alias (str): 配置别名。

        Returns:
            Optional[LLMConfig]: 如果找到则返回配置实体，否则返回 None。
        """

    @abstractmethod
    async def save(self, config: LLMConfig) -> LLMConfig:
        """
        保存 LLM 配置。如果别名已存在则更新，否则新增 (Upsert)。

        Args:
            config (LLMConfig): 需要保存的配置实体。

        Returns:
            LLMConfig: 保存后的配置实体（包含更新后的 ID 和时间戳）。
        """

    @abstractmethod
    async def delete_by_alias(self, alias: str) -> bool:
        """
        根据别名删除 LLM 配置。

        Args:
            alias (str): 要删除的配置别名。

        Returns:
            bool: 如果删除成功返回 True，如果配置不存在返回 False。
        """
