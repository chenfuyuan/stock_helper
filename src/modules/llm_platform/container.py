"""
LLM 平台模块 Composition Root。

统一封装 LLM 服务、注册表、配置服务等的组装逻辑，
供 Research 等模块通过本 Container 获取 LLM 能力，main 启动时通过本 Container 初始化注册表。
"""

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.llm_platform.application.services.config_service import (
    ConfigService,
)
from src.modules.llm_platform.application.services.llm_service import (
    LLMService,
)
from src.modules.llm_platform.application.services.web_search_service import (
    WebSearchService,
)
from src.modules.llm_platform.infrastructure.adapters.bocha_web_search import (
    BochaWebSearchAdapter,
)
from src.modules.llm_platform.infrastructure.adapters.caching_web_search_provider import (
    CachingWebSearchProvider,
)
from src.modules.llm_platform.infrastructure.config import llm_config
from src.modules.llm_platform.infrastructure.persistence.repositories.pg_config_repo import (
    PgLLMConfigRepository,
)
from src.modules.llm_platform.infrastructure.persistence.repositories.web_search_cache_repository import (  # noqa: E501
    PgWebSearchCacheRepository,
)
from src.modules.llm_platform.infrastructure.registry import LLMRegistry


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
        """
        获取 LLM 门面服务，内部使用全局 LLMRegistry 单例。
        若构造时提供了 session，则注入 PgLLMCallLogRepository 以记录调用审计日志。
        """
        if self._session is not None:
            from src.modules.llm_platform.infrastructure.persistence.repositories.llm_call_log_repository import (  # noqa: E501
                PgLLMCallLogRepository,
            )

            call_log_repo = PgLLMCallLogRepository(self._session)
            return LLMService(call_log_repository=call_log_repo)
        return LLMService()

    def config_service(self) -> ConfigService:
        """获取配置管理服务（需在构造时传入 session）。"""
        if self._session is None:
            raise RuntimeError("LLMPlatformContainer 需要 session 才能提供 config_service")
        repo = PgLLMConfigRepository(self._session)
        registry = LLMRegistry()
        registry.set_repository(repo)
        return ConfigService(repo=repo, registry=registry)

    def web_search_service(self) -> WebSearchService:
        """
        获取 Web 搜索服务，内部构造博查搜索适配器。
        有 session 时用 CachingWebSearchProvider 包装以启用搜索结果缓存；无 session 时不启用缓存。
        若构造时提供了 session，则注入 PgExternalAPICallLogRepository 以记录外部 API 调用日志。
        """
        adapter = BochaWebSearchAdapter(
            api_key=llm_config.BOCHA_API_KEY,
            base_url=llm_config.BOCHA_BASE_URL,
        )
        if self._session is not None:
            cache_repo = PgWebSearchCacheRepository(self._session)
            adapter = CachingWebSearchProvider(inner=adapter, cache_repo=cache_repo)
            from src.shared.infrastructure.persistence.external_api_call_log_repository import (
                PgExternalAPICallLogRepository,
            )

            api_call_log_repo = PgExternalAPICallLogRepository(self._session)
            return WebSearchService(provider=adapter, api_call_log_repository=api_call_log_repo)
        return WebSearchService(provider=adapter)
