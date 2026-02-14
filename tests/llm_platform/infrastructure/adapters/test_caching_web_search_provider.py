"""
CachingWebSearchProvider 单元测试。

4.3 缓存命中不调用 inner、未命中调用 inner 并写入、写入失败不阻塞、搜索失败不写缓存。
"""
from unittest.mock import AsyncMock

import pytest

from src.modules.llm_platform.domain.web_search_dtos import (
    WebSearchRequest,
    WebSearchResponse,
    WebSearchResultItem,
)
from src.modules.llm_platform.infrastructure.adapters.caching_web_search_provider import (
    CachingWebSearchProvider,
)


@pytest.fixture
def mock_inner():
    return AsyncMock()


@pytest.fixture
def mock_cache_repo():
    return AsyncMock()


@pytest.mark.asyncio
async def test_cache_hit_does_not_call_inner(mock_inner, mock_cache_repo):
    """缓存命中时直接返回缓存结果，不调用 inner provider。"""
    from datetime import datetime, timezone

    from src.modules.llm_platform.domain.dtos.web_search_cache_entry import WebSearchCacheEntry
    from src.modules.llm_platform.domain.web_search_cache_utils import compute_cache_key

    request = WebSearchRequest(query="货币", freshness="oneDay")
    cached_response = WebSearchResponse(query="货币", total_matches=0, results=[])
    key = compute_cache_key(request)
    now = datetime.now(timezone.utc)
    entry = WebSearchCacheEntry(
        cache_key=key,
        request_params=request.model_dump(),
        response_data=cached_response.model_dump_json(),
        created_at=now,
        expires_at=now,
    )
    mock_cache_repo.get = AsyncMock(return_value=entry)
    provider = CachingWebSearchProvider(inner=mock_inner, cache_repo=mock_cache_repo)

    response = await provider.search(request)

    mock_inner.search.assert_not_awaited()
    assert response.query == "货币"
    assert response.total_matches == 0


@pytest.mark.asyncio
async def test_cache_miss_calls_inner_and_puts(mock_inner, mock_cache_repo):
    """缓存未命中时调用 inner 并写入缓存。"""
    request = WebSearchRequest(query="宏观", freshness="oneWeek")
    search_response = WebSearchResponse(
        query="宏观",
        total_matches=1,
        results=[WebSearchResultItem(title="T", url="https://u", snippet="s")],
    )
    mock_inner.search = AsyncMock(return_value=search_response)
    mock_cache_repo.get = AsyncMock(return_value=None)
    mock_cache_repo.put = AsyncMock()
    provider = CachingWebSearchProvider(inner=mock_inner, cache_repo=mock_cache_repo)

    response = await provider.search(request)

    mock_inner.search.assert_awaited_once_with(request)
    mock_cache_repo.put.assert_awaited_once()
    put_entry = mock_cache_repo.put.await_args[0][0]
    assert put_entry.response_data == search_response.model_dump_json()
    assert response.query == "宏观"
    assert len(response.results) == 1


@pytest.mark.asyncio
async def test_put_failure_does_not_block_return(mock_inner, mock_cache_repo):
    """缓存写入失败时不阻塞，搜索结果正常返回。"""
    request = WebSearchRequest(query="行业")
    search_response = WebSearchResponse(query="行业", total_matches=0, results=[])
    mock_inner.search = AsyncMock(return_value=search_response)
    mock_cache_repo.get = AsyncMock(return_value=None)
    mock_cache_repo.put = AsyncMock(side_effect=Exception("DB error"))
    provider = CachingWebSearchProvider(inner=mock_inner, cache_repo=mock_cache_repo)

    response = await provider.search(request)

    assert response.query == "行业"
    mock_cache_repo.put.assert_awaited_once()


@pytest.mark.asyncio
async def test_search_failure_does_not_put(mock_inner, mock_cache_repo):
    """搜索失败（inner 抛异常）时不写入缓存。"""
    request = WebSearchRequest(query="失败")
    mock_inner.search = AsyncMock(side_effect=Exception("网络错误"))
    mock_cache_repo.get = AsyncMock(return_value=None)
    mock_cache_repo.put = AsyncMock()
    provider = CachingWebSearchProvider(inner=mock_inner, cache_repo=mock_cache_repo)

    with pytest.raises(Exception, match="网络错误"):
        await provider.search(request)

    mock_cache_repo.put.assert_not_awaited()
