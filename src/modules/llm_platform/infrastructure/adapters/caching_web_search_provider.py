"""
CachingWebSearchProvider：实现 IWebSearchProvider，包装实际 Provider 与缓存仓储，透明缓存博查搜索结果。
"""

from datetime import datetime, timezone

from loguru import logger

from src.modules.llm_platform.domain.dtos.web_search_cache_entry import (
    WebSearchCacheEntry,
)
from src.modules.llm_platform.domain.ports.web_search import IWebSearchProvider
from src.modules.llm_platform.domain.ports.web_search_cache_repository import (
    IWebSearchCacheRepository,
)
from src.modules.llm_platform.domain.web_search_cache_utils import (
    compute_cache_key,
    compute_expires_at,
)
from src.modules.llm_platform.domain.web_search_dtos import (
    WebSearchRequest,
    WebSearchResponse,
)


class CachingWebSearchProvider(IWebSearchProvider):
    """
    带缓存的 Web 搜索 Provider 装饰器。

    先查缓存，命中则直接返回；未命中则委托 inner provider 搜索后写入缓存。
    缓存写入失败仅记录 WARNING，不阻塞返回；搜索失败不写缓存。
    """

    def __init__(
        self,
        inner: IWebSearchProvider,
        cache_repo: IWebSearchCacheRepository,
    ) -> None:
        self._inner = inner
        self._cache_repo = cache_repo

    async def search(self, request: WebSearchRequest) -> WebSearchResponse:
        """
        执行搜索：先查缓存，命中返回；未命中则调用 inner 并写入缓存。
        """
        cache_key = compute_cache_key(request)
        entry = await self._cache_repo.get(cache_key)
        if entry is not None:
            logger.info(
                "博查搜索缓存命中，查询词: {}, cache_key: {}, 直接返回缓存结果",
                request.query,
                cache_key,
            )
            return WebSearchResponse.model_validate_json(entry.response_data)

        logger.info(
            "博查搜索缓存未命中，查询词: {}，将调用博查 API", request.query
        )
        response = await self._inner.search(request)
        # 使用 naive UTC 以匹配 DB 的 TIMESTAMP WITHOUT TIME ZONE，避免 asyncpg 的 offset-naive/aware 混用报错
        created_at = datetime.now(timezone.utc).replace(tzinfo=None)
        expires_at = compute_expires_at(created_at, request.freshness)
        cache_entry = WebSearchCacheEntry(
            cache_key=cache_key,
            request_params=request.model_dump(),
            response_data=response.model_dump_json(),
            created_at=created_at,
            expires_at=expires_at,
        )
        try:
            await self._cache_repo.put(cache_entry)
        except Exception as e:
            logger.warning(
                "博查搜索缓存写入失败，不阻塞返回，query: {}, error: {}",
                request.query,
                str(e),
            )
        return response
