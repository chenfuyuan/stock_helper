"""
Web 搜索缓存仓储 Port。

定义搜索结果缓存的持久化契约，仅依赖 Domain 层 DTO，不依赖 Infrastructure。
"""

from abc import ABC, abstractmethod

from src.modules.llm_platform.domain.dtos.web_search_cache_entry import (
    WebSearchCacheEntry,
)


class IWebSearchCacheRepository(ABC):
    """
    Web 搜索缓存仓储抽象接口。

    实现方负责按 cache_key 查询未过期条目、写入/覆盖条目、清理过期条目。
    """

    @abstractmethod
    async def get(self, cache_key: str) -> WebSearchCacheEntry | None:
        """
        按缓存键查询未过期的缓存条目。

        Args:
            cache_key: 请求参数哈希（64 字符十六进制）。

        Returns:
            未过期则返回 WebSearchCacheEntry，过期或不存在返回 None。
        """

    @abstractmethod
    async def put(self, entry: WebSearchCacheEntry) -> None:
        """
        写入或覆盖缓存条目。

        Args:
            entry: 缓存条目（含 cache_key、request_params、response_data、created_at、expires_at）。
        """

    @abstractmethod
    async def cleanup_expired(self) -> int:
        """
        清理已过期的缓存条目。

        Returns:
            删除的条数。
        """
