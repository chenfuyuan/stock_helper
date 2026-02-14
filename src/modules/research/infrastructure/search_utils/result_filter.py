"""
搜索结果过滤器。

实现规则式过滤：URL 去重、去空标题、去无内容（summary + snippet 均空）。
过滤后按 published_date 降序排序（无日期排末尾）。
"""
import logging
from typing import List
from urllib.parse import urlparse

from src.modules.llm_platform.domain.web_search_dtos import WebSearchResultItem

logger = logging.getLogger(__name__)


class SearchResultFilter:
    """
    搜索结果过滤器。
    
    提供规则式过滤和排序功能，提升搜索结果质量。
    """

    def filter_and_sort(self, items: List[WebSearchResultItem]) -> List[WebSearchResultItem]:
        """
        过滤并排序搜索结果。
        
        过滤规则（按序执行）：
        1. URL 去重：同一 URL 仅保留首次出现的条目
        2. 去空标题：title 为空或全空白的条目被剔除
        3. 去无内容：summary 和 snippet 均为空的条目被剔除
        
        排序规则：按 published_date 降序排列，无日期的条目排在末尾。
        
        Args:
            items: 原始搜索结果列表
            
        Returns:
            List[WebSearchResultItem]: 过滤并排序后的结果列表
        """
        if not items:
            return []

        # 1. URL 去重
        seen_urls = set()
        dedup_items = []
        for item in items:
            try:
                # 标准化 URL（去除 fragment）
                parsed = urlparse(item.url)
                normalized_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                if normalized_url not in seen_urls:
                    seen_urls.add(normalized_url)
                    dedup_items.append(item)
            except Exception as e:
                # URL 解析失败时保留条目，避免误杀
                logger.debug(f"URL 解析失败，保留条目: {item.url}, 错误: {e}")
                if item.url not in seen_urls:
                    seen_urls.add(item.url)
                    dedup_items.append(item)

        # 2. 去空标题
        filtered_items = [
            item for item in dedup_items
            if item.title and item.title.strip()
        ]

        # 3. 去无内容
        final_items = [
            item for item in filtered_items
            if (item.summary and item.summary.strip()) or (item.snippet and item.snippet.strip())
        ]

        # 4. 按时效排序
        sorted_items = self._sort_by_published_date(final_items)

        logger.debug(
            f"搜索结果过滤完成：原始={len(items)}, "
            f"去重后={len(dedup_items)}, "
            f"去空标题后={len(filtered_items)}, "
            f"去无内容后={len(final_items)}"
        )

        return sorted_items

    def _sort_by_published_date(self, items: List[WebSearchResultItem]) -> List[WebSearchResultItem]:
        """
        按 published_date 降序排序，无日期的条目排在末尾。
        
        Args:
            items: 待排序的搜索结果列表
            
        Returns:
            List[WebSearchResultItem]: 排序后的结果列表
        """
        def sort_key(item: WebSearchResultItem):
            # 有日期的条目按日期降序（最近的在前），无日期的条目排在最后
            if item.published_date:
                return (0, item.published_date)  # 0 表示有日期
            else:
                return (1, "")  # 1 表示无日期，排在最后

        return sorted(items, key=sort_key, reverse=False)
