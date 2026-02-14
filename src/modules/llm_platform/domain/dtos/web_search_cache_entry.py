"""
Web 搜索缓存条目 DTO。

用于 IWebSearchCacheRepository 的 get/put 契约，存储请求参数哈希、原始参数、
WebSearchResponse 的 JSON 序列化及创建/过期时间。
"""

from datetime import datetime

from pydantic import BaseModel


class WebSearchCacheEntry(BaseModel):
    """
    Web 搜索缓存条目。

    Attributes:
        cache_key: 请求参数的 SHA-256 十六进制摘要，主键。
        request_params: 原始请求参数字典，便于调试。
        response_data: WebSearchResponse 的 JSON 序列化字符串。
        created_at: 缓存写入时间。
        expires_at: 缓存过期时间。
    """

    cache_key: str
    request_params: dict
    response_data: str
    created_at: datetime
    expires_at: datetime
