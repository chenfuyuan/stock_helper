"""
Web 搜索缓存键与 TTL 计算。

基于 WebSearchRequest 的 query、freshness、summary、count 生成确定性缓存键（SHA-256 十六进制），
并根据 freshness 计算 TTL（timedelta），供 CachingWebSearchProvider 与 Repository 使用。
"""
import hashlib
from datetime import datetime, timedelta
from typing import Optional

from src.modules.llm_platform.domain.web_search_dtos import WebSearchRequest


# freshness -> TTL 小时数（与 design 一致）
_FRESHNESS_TTL_HOURS = {
    "oneDay": 4,
    "oneWeek": 12,
    "oneMonth": 24,
    "oneYear": 48,
    "noLimit": 24,
}
_DEFAULT_TTL_HOURS = 24


def compute_cache_key(request: WebSearchRequest) -> str:
    """
    根据请求四元组生成确定性缓存键（SHA-256 十六进制，64 字符）。

    相同 query、freshness、summary、count 始终得到相同 key。

    Args:
        request: 搜索请求 DTO。

    Returns:
        64 字符十六进制字符串。
    """
    raw = f"{request.query}|{request.freshness or ''}|{request.summary}|{request.count}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def compute_ttl_seconds(freshness: Optional[str]) -> int:
    """
    根据 freshness 返回 TTL 秒数。

    映射规则：oneDay=4h, oneWeek=12h, oneMonth=24h, oneYear=48h, noLimit/None=24h。

    Args:
        freshness: 请求的 freshness 参数，可为 None。

    Returns:
        TTL 秒数。
    """
    hours = _FRESHNESS_TTL_HOURS.get(freshness, _DEFAULT_TTL_HOURS)
    return hours * 3600


def compute_expires_at(created_at: datetime, freshness: Optional[str]) -> datetime:
    """
    根据创建时间和 freshness 计算过期时间。

    Args:
        created_at: 缓存写入时间。
        freshness: 请求的 freshness 参数。

    Returns:
        过期时间（created_at + TTL）。
    """
    delta = timedelta(seconds=compute_ttl_seconds(freshness))
    return created_at + delta
