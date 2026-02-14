from datetime import date
from typing import Dict, List, Set

from src.modules.research.domain.dtos.catalyst_context import (
    CatalystContextDTO,
)
from src.modules.research.domain.dtos.catalyst_inputs import (
    CatalystSearchResult,
    CatalystSearchResultItem,
    CatalystStockOverview,
)
from src.modules.research.domain.ports.catalyst_context_builder import (
    ICatalystContextBuilder,
)


class CatalystContextBuilderImpl(ICatalystContextBuilder):
    def build(
        self,
        overview: CatalystStockOverview,
        search_results: List[CatalystSearchResult],
    ) -> CatalystContextDTO:
        # 1. Initialize context parts with default message
        # Internal keys to track the four dimensions
        context_map: Dict[str, str] = {
            "company_events": "该维度暂无搜索结果，信息有限",
            "industry_catalyst": "该维度暂无搜索结果，信息有限",
            "market_sentiment": "该维度暂无搜索结果，信息有限",
            "earnings": "该维度暂无搜索结果，信息有限",
        }

        # Mapping from dimension_topic (from Adapter) to internal key
        # These keys must match what the Adapter produces in dimension_topic
        topic_map = {
            "公司重大事件与动态": "company_events",
            "行业催化与竞争格局": "industry_catalyst",
            "市场情绪与机构动向": "market_sentiment",
            "财报预期与业绩催化": "earnings",
        }

        all_urls: Set[str] = set()

        for result in search_results:
            key = topic_map.get(result.dimension_topic)
            if not key:
                continue

            if not result.items:
                continue

            formatted_text = self._format_items(result.items)
            context_map[key] = formatted_text

            for item in result.items:
                if item.url:
                    all_urls.add(item.url)

        # 2. Format URL list
        sorted_urls = sorted(list(all_urls))
        urls_text = "\n".join([f"- {url}" for url in sorted_urls]) if sorted_urls else "无引用来源"

        # 3. Build DTO
        return CatalystContextDTO(
            stock_name=overview.stock_name,
            third_code=overview.third_code,
            industry=overview.industry,
            current_date=date.today().isoformat(),
            company_events_context=context_map["company_events"],
            industry_catalyst_context=context_map["industry_catalyst"],
            market_sentiment_context=context_map["market_sentiment"],
            earnings_context=context_map["earnings"],
            all_source_urls=urls_text,
        )

    def _format_items(self, items: List[CatalystSearchResultItem]) -> str:
        lines = []
        for i, item in enumerate(items, 1):
            date_str = f" ({item.published_date})" if item.published_date else ""
            source_str = f" - 来源: {item.site_name}" if item.site_name else ""
            summary = item.summary or item.snippet or "无摘要"

            lines.append(f"[{i}] {item.title}{source_str}{date_str}")
            lines.append(f"    {summary}")
            lines.append("")
        return "\n".join(lines).strip()
