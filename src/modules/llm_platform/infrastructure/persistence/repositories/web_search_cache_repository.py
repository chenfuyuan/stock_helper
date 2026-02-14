"""
PostgreSQL 实现的 Web 搜索缓存仓储。

实现 IWebSearchCacheRepository：get 按 key 且未过期查询、put 使用 UPSERT、cleanup_expired 删除过期条目。
"""

import logging

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.llm_platform.domain.dtos.web_search_cache_entry import (
    WebSearchCacheEntry,
)
from src.modules.llm_platform.domain.ports.web_search_cache_repository import (
    IWebSearchCacheRepository,
)
from src.modules.llm_platform.infrastructure.persistence.models.web_search_cache_model import (
    WebSearchCacheModel,
)

logger = logging.getLogger(__name__)


class PgWebSearchCacheRepository(IWebSearchCacheRepository):
    """基于 PostgreSQL 的 Web 搜索缓存仓储。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, cache_key: str) -> WebSearchCacheEntry | None:
        """
        按缓存键查询未过期的条目；过期或不存在返回 None。
        """
        stmt = (
            select(WebSearchCacheModel)
            .where(WebSearchCacheModel.cache_key == cache_key)
            .where(WebSearchCacheModel.expires_at > func.now())
        )
        result = await self._session.execute(stmt)
        row = result.scalars().first()
        return row.to_dto() if row else None

    async def put(self, entry: WebSearchCacheEntry) -> None:
        """
        使用 UPSERT 写入或覆盖缓存条目。
        """
        stmt = insert(WebSearchCacheModel).values(
            cache_key=entry.cache_key,
            request_params=entry.request_params,
            response_data=entry.response_data,
            created_at=entry.created_at,
            expires_at=entry.expires_at,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["cache_key"],
            set_={
                "request_params": entry.request_params,
                "response_data": entry.response_data,
                "created_at": entry.created_at,
                "expires_at": entry.expires_at,
            },
        )
        await self._session.execute(stmt)
        await self._session.commit()

    async def cleanup_expired(self) -> int:
        """
        删除 expires_at <= now() 的条目，返回删除条数。
        """
        stmt = delete(WebSearchCacheModel).where(
            WebSearchCacheModel.expires_at <= func.now()
        )
        result = await self._session.execute(stmt)
        await self._session.commit()
        return result.rowcount or 0
