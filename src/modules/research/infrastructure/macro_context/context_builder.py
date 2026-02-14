"""
宏观上下文构建实现。

将股票概览与搜索结果转为 MacroContextDTO，用于填充 User Prompt 模板。
处理逻辑包括：按维度归类、格式化文本段落、收集来源 URL、处理空结果。
"""

import logging
from datetime import date
from typing import Dict, List, Set

from src.modules.research.domain.dtos.macro_context import MacroContextDTO
from src.modules.research.domain.dtos.macro_inputs import (
    MacroSearchResult,
    MacroSearchResultItem,
    MacroStockOverview,
)
from src.modules.research.domain.ports.macro_context_builder import (
    IMacroContextBuilder,
)

logger = logging.getLogger(__name__)

# 空结果标记文本
EMPTY_DIMENSION_TEXT = "该维度暂无搜索结果，信息有限。"


class MacroContextBuilderImpl(IMacroContextBuilder):
    """
    宏观上下文构建器实现。

    将搜索结果按维度归类并格式化为文本上下文，
    收集来源 URL，处理空结果，填充基础字段。
    """

    def build(
        self,
        overview: MacroStockOverview,
        search_results: List[MacroSearchResult],
    ) -> MacroContextDTO:
        """
        构建宏观上下文。

        将股票概览和搜索结果转为 MacroContextDTO，用于填充 User Prompt 模板。

        Args:
            overview: 股票概览信息（名称、行业、代码）
            search_results: 四个维度的搜索结果列表

        Returns:
            MacroContextDTO: 包含 9 个字段的宏观上下文（与 user.md 占位符一一对应）
        """
        # 1. 按维度归类搜索结果
        dimension_map = self._group_by_dimension(search_results)

        # 2. 格式化各维度的文本上下文
        monetary_context = self._format_dimension_context(
            dimension_map.get("货币与流动性", [])
        )
        policy_context = self._format_dimension_context(
            dimension_map.get("产业政策", [])
        )
        economic_context = self._format_dimension_context(
            dimension_map.get("宏观经济", [])
        )
        industry_context = self._format_dimension_context(
            dimension_map.get("行业景气", [])
        )

        # 3. 收集所有来源 URL（去重）
        all_source_urls = self._collect_source_urls(search_results)

        # 4. 填充基础字段
        current_date = date.today().strftime("%Y-%m-%d")

        # 来源 URL 数：每行一个 URL，新行数 + 1；无 URL 时为 0（f-string 表达式中不能含反斜杠，故提前计算）
        newline_char = "\n"
        url_count = (
            all_source_urls.count(newline_char) + 1
            if newline_char in all_source_urls
            else 0
        )
        logger.info(
            f"宏观上下文构建完成：{overview.stock_name}，"
            f"搜索结果数：货币={len(dimension_map.get('货币与流动性', []))}，"
            f"政策={len(dimension_map.get('产业政策', []))}，"
            f"经济={len(dimension_map.get('宏观经济', []))}，"
            f"行业={len(dimension_map.get('行业景气', []))}，"
            f"来源URL数={url_count}"
        )

        return MacroContextDTO(
            stock_name=overview.stock_name,
            third_code=overview.third_code,
            industry=overview.industry,
            current_date=current_date,
            monetary_context=monetary_context,
            policy_context=policy_context,
            economic_context=economic_context,
            industry_context=industry_context,
            all_source_urls=all_source_urls,
        )

    def _group_by_dimension(
        self, search_results: List[MacroSearchResult]
    ) -> Dict[str, List[MacroSearchResultItem]]:
        """
        按维度归类搜索结果。

        将 List[MacroSearchResult] 转为 Dict[dimension_topic, items]，
        便于后续按维度格式化。

        Args:
            search_results: 搜索结果列表

        Returns:
            Dict[str, List[MacroSearchResultItem]]: 维度 -> 搜索条目列表的映射
        """
        dimension_map: Dict[str, List[MacroSearchResultItem]] = {}

        for result in search_results:
            # 将 dimension_topic 映射为标准维度名称（便于后续处理）
            dimension_key = self._normalize_dimension_name(
                result.dimension_topic
            )
            dimension_map[dimension_key] = result.items

        return dimension_map

    def _normalize_dimension_name(self, dimension_topic: str) -> str:
        """
        将 dimension_topic 归一化为标准维度名称。

        根据 dimension_topic 包含的关键词判断所属维度。

        Args:
            dimension_topic: 维度主题字符串

        Returns:
            str: 标准维度名称（货币与流动性、产业政策、宏观经济、行业景气）
        """
        topic_lower = dimension_topic.lower()

        if "货币" in topic_lower or "流动性" in topic_lower:
            return "货币与流动性"
        elif (
            "产业" in topic_lower
            or "政策" in topic_lower
            or "监管" in topic_lower
        ):
            return "产业政策"
        elif (
            "宏观" in topic_lower
            or "经济" in topic_lower
            or "gdp" in topic_lower
            or "pmi" in topic_lower
        ):
            return "宏观经济"
        elif "行业" in topic_lower or "景气" in topic_lower:
            return "行业景气"
        else:
            # 未匹配到标准维度时，使用原始 topic
            logger.warning(f"未识别的维度主题：{dimension_topic}，使用原值")
            return dimension_topic

    def _format_dimension_context(
        self, items: List[MacroSearchResultItem]
    ) -> str:
        """
        格式化单个维度的搜索结果为文本段落。

        将搜索条目列表转为格式化的文本段落（标题 + 来源 + 日期 + 摘要）。
        若 items 为空，返回"该维度暂无搜索结果，信息有限"。

        Args:
            items: 该维度的搜索条目列表

        Returns:
            str: 格式化后的文本段落
        """
        if not items:
            return EMPTY_DIMENSION_TEXT

        formatted_items = []
        for idx, item in enumerate(items, start=1):
            # 构建单条结果的格式化文本
            item_text = f"{idx}. **{item.title}**"

            # 添加来源和日期（若有）
            metadata_parts = []
            if item.site_name:
                metadata_parts.append(f"来源：{item.site_name}")
            if item.published_date:
                metadata_parts.append(f"日期：{item.published_date}")

            if metadata_parts:
                item_text += f"\n   ({' | '.join(metadata_parts)})"

            # 添加摘要内容（优先使用 AI 摘要，其次使用 snippet）
            content = item.summary if item.summary else item.snippet
            if content:
                item_text += f"\n   {content}"

            # 添加 URL
            item_text += f"\n   URL: {item.url}"

            formatted_items.append(item_text)

        return "\n\n".join(formatted_items)

    def _collect_source_urls(
        self, search_results: List[MacroSearchResult]
    ) -> str:
        """
        收集所有搜索结果的来源 URL（去重）。

        从所有搜索结果中提取去重的 URL 列表，格式化为字符串。

        Args:
            search_results: 搜索结果列表

        Returns:
            str: 去重后的 URL 列表字符串（每行一个 URL）
        """
        urls: Set[str] = set()

        for result in search_results:
            for item in result.items:
                if item.url:
                    urls.add(item.url)

        if not urls:
            return "（暂无来源 URL）"

        # 转为有序列表并格式化
        sorted_urls = sorted(urls)
        formatted_urls = "\n".join(f"- {url}" for url in sorted_urls)

        logger.info(f"收集到 {len(sorted_urls)} 个去重后的来源 URL")

        return formatted_urls
