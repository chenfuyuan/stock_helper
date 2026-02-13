import logging
from datetime import date
from typing import List, Optional

from src.modules.research.domain.ports.catalyst_data import ICatalystDataPort
from src.modules.research.domain.dtos.catalyst_inputs import (
    CatalystStockOverview,
    CatalystSearchResult,
    CatalystSearchResultItem,
)
from src.modules.data_engineering.application.queries.get_stock_basic_info import (
    GetStockBasicInfoUseCase,
)
from src.modules.llm_platform.application.services.web_search_service import (
    WebSearchService,
)
from src.modules.llm_platform.domain.web_search_dtos import (
    WebSearchRequest,
    WebSearchResultItem,
)

logger = logging.getLogger(__name__)


class CatalystDataAdapter(ICatalystDataPort):
    def __init__(
        self,
        stock_info_use_case: GetStockBasicInfoUseCase,
        web_search_service: WebSearchService,
    ):
        self.stock_info_use_case = stock_info_use_case
        self.web_search_service = web_search_service

    async def get_stock_overview(self, symbol: str) -> Optional[CatalystStockOverview]:
        """
        获取股票基础概览信息
        内部调用 data_engineering 的 GetStockBasicInfoUseCase
        """
        try:
            result = await self.stock_info_use_case.execute(symbol)
            if not result or not result.info:
                logger.warning(f"Stock basic info not found for symbol: {symbol}")
                return None

            info = result.info
             # Handle None for industry, default to "Unknown"
            industry_val = info.industry if info.industry else "Unknown"
            
            return CatalystStockOverview(
                stock_name=info.name,
                industry=industry_val,
                third_code=info.third_code,
            )
        except Exception as e:
            logger.error(f"Failed to get stock overview for {symbol}: {e}")
            return None

    async def search_catalyst_context(
        self, stock_name: str, industry: str
    ) -> List[CatalystSearchResult]:
        """
        执行多维度的催化剂搜索
        内部调用 llm_platform 的 WebSearchService
        """
        current_year = date.today().year

        # Define search dimensions and queries
        # Dimensions MUST match the keys used in CatalystContextBuilderImpl
        # (Company Events, Industry Catalysts, Market Sentiment, Earnings Expectations)

        # Mapping topics to query templates
        # Topic names here align with what ContextBuilder expects (based on design doc)
        search_configs = [
            {
                "topic": "公司重大事件与动态",
                "template": "{stock_name} 重大事件 并购重组 管理层变动 战略合作 {year}年",
            },
            {
                "topic": "行业催化与竞争格局",
                "template": "{stock_name} {industry} 竞争格局 技术突破 政策催化 {year}年",
            },
            {
                "topic": "市场情绪与机构动向",
                "template": "{stock_name} 机构评级 分析师 调研 资金流向 {year}年",
            },
            {
                "topic": "财报预期与业绩催化",
                "template": "{stock_name} 业绩预告 财报 盈利预测 订单合同 {year}年",
            },
        ]

        results = []

        for config in search_configs:
            topic = config["topic"]
            query = config["template"].format(
                stock_name=stock_name, industry=industry, year=current_year
            )

            try:
                # Execute search with configured parameters
                search_req = WebSearchRequest(
                    query=query,
                    freshness="oneMonth",  # As per design
                    count=8,  # As per design
                    summary=True,  # As per design
                )

                response = await self.web_search_service.search(search_req)

                items = [self._map_search_item(item) for item in response.results]

                results.append(CatalystSearchResult(dimension_topic=topic, items=items))

            except Exception as e:
                # Graceful degradation logic as per Decision 6
                logger.warning(
                    f"Catalyst search failed for dimension '{topic}' query='{query}': {e}"
                )
                results.append(CatalystSearchResult(dimension_topic=topic, items=[]))

        return results

    def _map_search_item(self, item: WebSearchResultItem) -> CatalystSearchResultItem:
        return CatalystSearchResultItem(
            title=item.title,
            url=item.url,
            snippet=item.snippet,
            summary=item.summary,
            site_name=item.site_name,
            published_date=item.published_date,
        )
