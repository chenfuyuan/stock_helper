"""
PgWebSearchCacheRepository 集成测试。

4.4 写入/读取、过期不返回、UPSERT 覆盖、cleanup_expired 删除过期条目。
"""

from datetime import datetime, timedelta

import pytest

from src.modules.llm_platform.domain.dtos.web_search_cache_entry import (
    WebSearchCacheEntry,
)
from src.modules.llm_platform.infrastructure.persistence.repositories.web_search_cache_repository import (  # noqa: E501
    PgWebSearchCacheRepository,
)


@pytest.mark.asyncio
async def test_put_and_get_returns_entry(db_session):
    """写入后在同一 TTL 内 get 能返回刚写入的条目。"""
    repo = PgWebSearchCacheRepository(db_session)
    now = datetime.utcnow()
    entry = WebSearchCacheEntry(
        cache_key="a" * 64,
        request_params={"query": "test"},
        response_data='{"query":"test","total_matches":0,"results":[]}',
        created_at=now,
        expires_at=now + timedelta(hours=24),
    )
    await repo.put(entry)
    got = await repo.get(entry.cache_key)
    assert got is not None
    assert got.cache_key == entry.cache_key
    assert got.response_data == entry.response_data


@pytest.mark.asyncio
async def test_expired_entry_returns_none(db_session):
    """已过期的条目 get 返回 None。"""
    repo = PgWebSearchCacheRepository(db_session)
    now = datetime.utcnow()
    entry = WebSearchCacheEntry(
        cache_key="b" * 64,
        request_params={},
        response_data="{}",
        created_at=now - timedelta(hours=25),
        expires_at=now - timedelta(hours=1),
    )
    await repo.put(entry)
    got = await repo.get(entry.cache_key)
    assert got is None


@pytest.mark.asyncio
async def test_upsert_overwrites(db_session):
    """同一 cache_key 再次 put 覆盖原条目。"""
    repo = PgWebSearchCacheRepository(db_session)
    key = "c" * 64
    now = datetime.utcnow()
    exp = now + timedelta(hours=24)
    await repo.put(
        WebSearchCacheEntry(
            cache_key=key,
            request_params={"v": 1},
            response_data="first",
            created_at=now,
            expires_at=exp,
        )
    )
    await repo.put(
        WebSearchCacheEntry(
            cache_key=key,
            request_params={"v": 2},
            response_data="second",
            created_at=now,
            expires_at=exp,
        )
    )
    got = await repo.get(key)
    assert got is not None
    assert got.response_data == "second"
    assert got.request_params == {"v": 2}


@pytest.mark.asyncio
async def test_cleanup_expired_deletes_and_returns_count(db_session):
    """cleanup_expired 删除过期条目并返回删除条数。"""
    repo = PgWebSearchCacheRepository(db_session)
    now = datetime.utcnow()
    past = now - timedelta(hours=1)
    key1 = "d" * 64
    key2 = "e" * 64
    await repo.put(
        WebSearchCacheEntry(
            cache_key=key1,
            request_params={},
            response_data="x",
            created_at=past,
            expires_at=past + timedelta(minutes=30),
        )
    )
    await repo.put(
        WebSearchCacheEntry(
            cache_key=key2,
            request_params={},
            response_data="y",
            created_at=now,
            expires_at=now + timedelta(hours=24),
        )
    )
    n = await repo.cleanup_expired()
    assert n >= 1
    assert await repo.get(key1) is None
    # key2 未过期，应仍存在（若 cleanup 只删过期则 key2 还在）
    got2 = await repo.get(key2)
    assert got2 is not None
    assert got2.response_data == "y"
