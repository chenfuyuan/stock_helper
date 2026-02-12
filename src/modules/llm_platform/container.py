"""
LLM 平台模块 Composition Root。

统一封装 LLM 服务、注册表、配置服务等的组装逻辑，
供 Research 等模块通过本 Container 获取 LLM 能力，main 启动时通过本 Container 初始化注册表。
"""
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.llm_platform.application.services.llm_service import LLMService
from src.modules.llm_platform.application.services.config_service import ConfigService
from src.modules.llm_platform.infrastructure.registry import LLMRegistry
from src.modules.llm_platform.infrastructure.persistence.repositories.pg_config_repo import (
    PgLLMConfigRepository,
)


class LLMPlatformContainer:
    """LLM 平台模块的依赖组装容器。"""

    def __init__(self, session: Optional[AsyncSession] = None) -> None:
        self._session = session

    def llm_registry(self) -> LLMRegistry:
        """
        获取 LLM 注册表。若构造时提供了 session，则设置配置仓储（用于从 DB 加载配置）。
        启动时调用此方法后应执行 registry.refresh()。
        """
        registry = LLMRegistry()
        if self._session is not None:
            registry.set_repository(PgLLMConfigRepository(self._session))
        return registry

    def llm_service(self) -> LLMService:
        """获取 LLM 门面服务，内部使用全局 LLMRegistry 单例。"""
        return LLMService()

    def config_service(self) -> ConfigService:
        """获取配置管理服务（需在构造时传入 session）。"""
        if self._session is None:
            raise RuntimeError("LLMPlatformContainer 需要 session 才能提供 config_service")
        repo = PgLLMConfigRepository(self._session)
        registry = LLMRegistry()
        registry.set_repository(repo)
        return ConfigService(repo=repo, registry=registry)
