"""
获取宏观数据 Port 的 Adapter。

内部调用 data_engineering 的 GetStockBasicInfoUseCase（获取股票概览）
和 llm_platform 的 WebSearchService（执行多维度宏观搜索）。
不直接依赖上游模块的 repository 或 domain。
"""

import logging
from datetime import date
from typing import List, Optional

from src.modules.data_engineering.application.queries.get_stock_basic_info import (
    GetStockBasicInfoUseCase,
)
from src.modules.llm_platform.application.services.web_search_service import (
    WebSearchService,
)
from src.modules.llm_platform.domain.exceptions import (
    WebSearchConfigError,
    WebSearchConnectionError,
    WebSearchError,
)
from src.modules.llm_platform.domain.web_search_dtos import (
    WebSearchRequest,
)
from src.modules.research.domain.dtos.macro_inputs import (
    MacroSearchResult,
    MacroSearchResultItem,
    MacroStockOverview,
)
from src.modules.research.domain.ports.macro_data import IMacroDataPort
from src.modules.research.infrastructure.search_utils.macro_search_dimensions import (
    MACRO_SEARCH_DIMENSIONS,
)
from src.modules.research.infrastructure.search_utils.result_filter import (
    SearchResultFilter,
)

logger = logging.getLogger(__name__)


class MacroDataAdapter(IMacroDataPort):
    """
    宏观数据 Adapter 实现。

    通过 data_engineering 获取股票基础信息，
    通过 llm_platform 执行四个维度的宏观搜索。
    """

    def __init__(
        self,
        stock_info_usecase: GetStockBasicInfoUseCase,
        web_search_service: WebSearchService,
        result_filter: SearchResultFilter,
    ):
        """
        初始化宏观数据 Adapter。

        Args:
            stock_info_usecase: data_engineering 的股票信息查询用例
            web_search_service: llm_platform 的 Web 搜索服务
            result_filter: 搜索结果过滤器
        """
        self._stock_info_usecase = stock_info_usecase
        self._web_search_service = web_search_service
        self._result_filter = result_filter

    async def get_stock_overview(self, symbol: str) -> Optional[MacroStockOverview]:
        """
        获取股票基础信息（名称、行业、代码），用于宏观分析的上下文构建。

        该方法内部调用 data_engineering 的 GetStockBasicInfoUseCase，
        提取所需字段转为 MacroStockOverview。

        Args:
            symbol: 股票代码（如 '000001.SZ'）

        Returns:
            MacroStockOverview: 股票概览信息
            None: 标的不存在时返回 None
        """
        logger.info(f"获取股票基础信息：symbol={symbol}")

        try:
            basic_info = await self._stock_info_usecase.execute(symbol)

            if basic_info is None:
                logger.warning(f"标的不存在：symbol={symbol}")
                return None

            if basic_info.daily is None:
                logger.warning("股票日线数据为空，无法构建宏观概览：symbol=%s", symbol)
                return None

            # 转为 MacroStockOverview
            overview = MacroStockOverview(
                stock_name=basic_info.info.name,
                industry=basic_info.info.industry or "未知行业",
                third_code=basic_info.daily.third_code,
            )

            logger.info(f"股票基础信息获取成功：{overview.stock_name}，行业={overview.industry}")

            return overview

        except Exception as e:
            logger.error(f"获取股票基础信息失败：symbol={symbol}，错误={e}")
            raise

    async def search_macro_context(self, industry: str, stock_name: str) -> List[MacroSearchResult]:
        """
        基于行业与公司上下文，执行四个维度的宏观搜索。

        该方法内部调用 llm_platform 的 WebSearchService，
        按四个维度分别构建搜索查询并执行。
        每个维度的搜索独立 try/except，失败时返回空结果（不中断其他维度）。

        Args:
            industry: 所属行业（用于构建行业相关搜索查询）
            stock_name: 股票名称（可选择性用于增加搜索精确度）

        Returns:
            List[MacroSearchResult]: 四个维度的搜索结果列表
        """
        logger.info(f"开始执行四维度宏观搜索：行业={industry}，股票={stock_name}")

        current_year = date.today().year

        results: List[MacroSearchResult] = []

        # 使用配置驱动的搜索循环
        for config in MACRO_SEARCH_DIMENSIONS:
            dimension = config.topic
            # 填充查询模板中的占位符
            query = config.query_template.format(
                industry=industry,
                stock_name=stock_name,
                current_year=current_year,
            )

            logger.info(f"执行搜索：维度={dimension}，查询={query}")

            try:
                # 调用搜索服务
                search_request = WebSearchRequest(
                    query=query,
                    freshness=config.freshness,
                    summary=True,
                    count=config.count,
                )

                search_response = await self._web_search_service.search(search_request)

                # 过滤和排序搜索结果
                filtered_items = self._result_filter.filter_and_sort(search_response.results)

                # 记录过滤统计日志
                logger.info(
                    f"维度 {dimension} 过滤统计："
                    f"过滤前={len(search_response.results)}，"
                    f"过滤后={len(filtered_items)}"
                )

                # 转为 MacroSearchResultItem 列表
                items = [
                    MacroSearchResultItem(
                        title=item.title,
                        url=item.url,
                        snippet=item.snippet,
                        summary=item.summary,
                        site_name=item.site_name,
                        published_date=item.published_date,
                    )
                    for item in filtered_items
                ]

                results.append(
                    MacroSearchResult(
                        dimension_topic=dimension,
                        items=items,
                    )
                )

                logger.info(f"维度 {dimension} 搜索成功，返回 {len(items)} 条结果")

            except (
                WebSearchError,
                WebSearchConnectionError,
                WebSearchConfigError,
            ) as e:
                # 单维度搜索失败，记录警告，返回空结果，不中断其他维度
                logger.warning(
                    f"维度 {dimension} 搜索失败（类型={type(e).__name__}，错误={e}），"
                    f"该维度返回空结果，继续其他维度搜索"
                )
                results.append(
                    MacroSearchResult(
                        dimension_topic=dimension,
                        items=[],
                    )
                )

            except Exception as e:
                # 未预期的异常，同样记录警告并返回空结果
                logger.warning(
                    f"维度 {dimension} 搜索发生未预期错误（错误={e}），"
                    f"该维度返回空结果，继续其他维度搜索"
                )
                results.append(
                    MacroSearchResult(
                        dimension_topic=dimension,
                        items=[],
                    )
                )

        # 统计搜索结果
        total_items = sum(len(r.items) for r in results)
        empty_dimensions = [r.dimension_topic for r in results if not r.items]

        logger.info(
            f"四维度宏观搜索完成：总结果数={total_items}，"
            f"空维度={empty_dimensions if empty_dimensions else '无'}"
        )

        return results
