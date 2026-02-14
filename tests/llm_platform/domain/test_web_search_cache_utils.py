"""
缓存键生成与 TTL 计算单元测试。

4.1 缓存键：相同请求→相同 key、不同参数→不同 key、key 为 64 字符十六进制。
4.2 TTL：各 freshness 对应的 TTL 正确。
"""

from datetime import datetime, timedelta

from src.modules.llm_platform.domain.web_search_cache_utils import (
    compute_cache_key,
    compute_expires_at,
    compute_ttl_seconds,
)
from src.modules.llm_platform.domain.web_search_dtos import WebSearchRequest


class TestComputeCacheKey:
    """4.1 缓存键生成单元测试。"""

    def test_same_request_same_key(self):
        """相同请求参数生成相同缓存键。"""
        r1 = WebSearchRequest(query="货币", freshness="oneDay", summary=True, count=10)
        r2 = WebSearchRequest(query="货币", freshness="oneDay", summary=True, count=10)
        assert compute_cache_key(r1) == compute_cache_key(r2)

    def test_different_freshness_different_key(self):
        """仅 freshness 不同时生成不同缓存键。"""
        r1 = WebSearchRequest(query="宏观", freshness="oneWeek", summary=True, count=10)
        r2 = WebSearchRequest(query="宏观", freshness="oneMonth", summary=True, count=10)
        assert compute_cache_key(r1) != compute_cache_key(r2)

    def test_different_query_different_key(self):
        """仅 query 不同时生成不同缓存键。"""
        r1 = WebSearchRequest(query="A", freshness="oneDay", summary=True, count=10)
        r2 = WebSearchRequest(query="B", freshness="oneDay", summary=True, count=10)
        assert compute_cache_key(r1) != compute_cache_key(r2)

    def test_key_is_64_hex_chars(self):
        """缓存键为 64 字符十六进制（SHA-256）。"""
        r = WebSearchRequest(query="任意", freshness=None, summary=False, count=5)
        key = compute_cache_key(r)
        assert len(key) == 64
        assert all(c in "0123456789abcdef" for c in key)


class TestComputeTtl:
    """4.2 TTL 计算单元测试。"""

    def test_one_day_4_hours(self):
        """freshness=oneDay → TTL 4 小时。"""
        assert compute_ttl_seconds("oneDay") == 4 * 3600

    def test_one_week_12_hours(self):
        """freshness=oneWeek → TTL 12 小时。"""
        assert compute_ttl_seconds("oneWeek") == 12 * 3600

    def test_one_month_24_hours(self):
        """freshness=oneMonth → TTL 24 小时。"""
        assert compute_ttl_seconds("oneMonth") == 24 * 3600

    def test_one_year_48_hours(self):
        """freshness=oneYear → TTL 48 小时。"""
        assert compute_ttl_seconds("oneYear") == 48 * 3600

    def test_no_limit_24_hours(self):
        """freshness=noLimit → TTL 24 小时。"""
        assert compute_ttl_seconds("noLimit") == 24 * 3600

    def test_none_freshness_default_24_hours(self):
        """freshness=None → 默认 TTL 24 小时。"""
        assert compute_ttl_seconds(None) == 24 * 3600

    def test_expires_at_one_day(self):
        """oneDay 时 expires_at = created_at + 4 小时。"""
        created = datetime(2026, 2, 14, 12, 0, 0)
        expires = compute_expires_at(created, "oneDay")
        assert expires == created + timedelta(hours=4)

    def test_expires_at_none_freshness(self):
        """freshness=None 时 expires_at = created_at + 24 小时。"""
        created = datetime(2026, 2, 14, 12, 0, 0)
        expires = compute_expires_at(created, None)
        assert expires == created + timedelta(hours=24)
