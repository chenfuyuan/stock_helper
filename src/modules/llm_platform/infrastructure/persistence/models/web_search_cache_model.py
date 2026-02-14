"""
Web 搜索缓存 ORM 模型，映射 web_search_cache 表。
"""
from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.dialects.postgresql import JSONB

from src.shared.infrastructure.db.base import Base
from src.modules.llm_platform.domain.dtos.web_search_cache_entry import WebSearchCacheEntry


class WebSearchCacheModel(Base):
    """web_search_cache 表映射。"""

    __tablename__ = "web_search_cache"

    cache_key = Column(String(64), primary_key=True, comment="请求参数 SHA-256 哈希")
    request_params = Column(JSONB, nullable=False, comment="原始请求参数")
    response_data = Column(Text, nullable=False, comment="WebSearchResponse JSON")
    created_at = Column(DateTime, nullable=False, comment="写入时间")
    expires_at = Column(DateTime, nullable=False, comment="过期时间")

    def to_dto(self) -> WebSearchCacheEntry:
        """转换为 Domain DTO。"""
        return WebSearchCacheEntry(
            cache_key=self.cache_key,
            request_params=self.request_params or {},
            response_data=self.response_data,
            created_at=self.created_at,
            expires_at=self.expires_at,
        )

    @staticmethod
    def from_dto(entry: WebSearchCacheEntry) -> "WebSearchCacheModel":
        """从 Domain DTO 构建 ORM 实例。"""
        return WebSearchCacheModel(
            cache_key=entry.cache_key,
            request_params=entry.request_params,
            response_data=entry.response_data,
            created_at=entry.created_at,
            expires_at=entry.expires_at,
        )
