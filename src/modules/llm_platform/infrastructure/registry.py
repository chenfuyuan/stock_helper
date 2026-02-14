from typing import Dict, List, Optional

from loguru import logger

from src.modules.llm_platform.domain.entities.llm_config import LLMConfig
from src.modules.llm_platform.domain.ports.llm import ILLMProvider
from src.modules.llm_platform.domain.ports.repositories.config_repo import (
    ILLMConfigRepository,
)
from src.modules.llm_platform.infrastructure.adapters.openai import (
    OpenAIProvider,
)


class LLMRegistry:
    """
    LLM 注册表 (Singleton)
    负责管理所有活跃的 LLM Provider 实例。
    支持从数据库动态加载配置并实例化 Provider。
    """

    _instance = None
    _providers: Dict[str, ILLMProvider] = {}
    _configs: Dict[str, LLMConfig] = {}
    _repo: Optional[ILLMConfigRepository] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LLMRegistry, cls).__new__(cls)
        return cls._instance

    def set_repository(self, repo: ILLMConfigRepository):
        """
        设置配置仓储，用于加载配置。

        Args:
            repo (ILLMConfigRepository): 仓储实例
        """
        self._repo = repo

    async def refresh(self):
        """
        从数据库重新加载所有激活的配置，并刷新 Provider 实例。
        这是一个全量刷新操作，会清除旧的实例。
        """
        if not self._repo:
            logger.warning("Repository not set for LLMRegistry, cannot refresh from DB")
            return

        logger.info("Starting LLM Registry refresh...")
        try:
            configs = await self._repo.get_active_configs()

            # Clear and rebuild
            self._providers.clear()
            self._configs.clear()

            success_count = 0
            for config in configs:
                if self._register(config):
                    success_count += 1

            logger.info(
                f"LLM Registry refreshed. Loaded {success_count} providers out of "
                f"{len(configs)} configs."
            )
        except Exception as e:
            logger.error(f"LLM 注册表刷新失败: {str(e)}")
            # 这里选择记录错误而不是抛出异常，以防启动流程被中断
            # 系统将继续使用之前的旧配置（如果存在）

    def _register(self, config: LLMConfig) -> bool:
        """
        注册单个 LLM 配置。

        Args:
            config (LLMConfig): 配置实体

        Returns:
            bool: 注册成功返回 True，失败返回 False
        """
        try:
            logger.debug(f"Registering LLM provider: {config.alias} ({config.provider_type})")
            if config.provider_type.lower() == "openai":
                provider = OpenAIProvider(
                    api_key=config.api_key,
                    base_url=config.base_url,
                    model=config.model_name,
                )
            else:
                logger.warning(
                    f"Unsupported provider type: {config.provider_type} for alias {config.alias}"
                )
                return False

            self._providers[config.alias] = provider
            self._configs[config.alias] = config
            return True
        except Exception as e:
            logger.error(f"LLM Provider {config.alias} 注册异常: {str(e)}")
            return False

    def get_provider(self, alias: str) -> Optional[ILLMProvider]:
        """
        根据别名获取 Provider 实例。
        """
        return self._providers.get(alias)

    def get_all_configs(self) -> List[LLMConfig]:
        """
        获取当前注册表中的所有配置。
        """
        return list(self._configs.values())
