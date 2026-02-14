import logging
from datetime import date
from typing import List, Optional

from sqlalchemy.exc import SQLAlchemyError

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
from src.modules.research.domain.dtos.catalyst_inputs import (
    CatalystSearchResult,
    CatalystSearchResultItem,
    CatalystStockOverview,
)
from src.modules.research.domain.ports.catalyst_data import ICatalystDataPort
from src.modules.research.infrastructure.search_utils.catalyst_search_dimensions import (
    CATALYST_SEARCH_DIMENSIONS,
)
from src.modules.research.infrastructure.search_utils.result_filter import (
    SearchResultFilter,
)

logger = logging.getLogger(__name__)


class CatalystDataAdapter(ICatalystDataPort):
    def __init__(
        self,
        stock_info_use_case: GetStockBasicInfoUseCase,
        web_search_service: WebSearchService,
        result_filter: SearchResultFilter,
    ):
        self.stock_info_use_case = stock_info_use_case
        self.web_search_service = web_search_service
        self.result_filter = result_filter

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
            industry_val = info.industry if info.industry else "未知行业"

            return CatalystStockOverview(
                stock_name=info.name,
                industry=industry_val,
                third_code=info.third_code,
            )
        except SQLAlchemyError as e:
            logger.error(
                "获取股票概览时发生数据库/查询错误：symbol=%s，错误=%s",
                symbol,
                e,
            )
            return None

    async def search_catalyst_context(
        self, stock_name: str, industry: str
    ) -> List[CatalystSearchResult]:
        """
        执行多维度的催化剂搜索
        内部调用 llm_platform 的 WebSearchService
        """
        current_year = date.today().year

        results = []

        # 使用配置驱动的搜索循环
        for config in CATALYST_SEARCH_DIMENSIONS:
            topic = config.topic
            # 填充查询模板中的占位符
            query = config.query_template.format(
                stock_name=stock_name,
                industry=industry,
                current_year=current_year,
            )

            try:
                # 调用搜索服务
                search_req = WebSearchRequest(
                    query=query,
                    freshness=config.freshness,
                    count=config.count,
                    summary=True,
                )

                response = await self.web_search_service.search(search_req)

                # 过滤和排序搜索结果
                filtered_items = self.result_filter.filter_and_sort(response.results)

                # 记录过滤统计日志
                logger.info(
                    f"维度 {topic} 过滤统计："
                    f"过滤前={len(response.results)}，"
                    f"过滤后={len(filtered_items)}"
                )

                items = [self._map_search_item(item) for item in filtered_items]

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
