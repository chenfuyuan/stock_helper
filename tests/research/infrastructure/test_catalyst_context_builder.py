from datetime import date

from src.modules.research.domain.dtos.catalyst_inputs import (
    CatalystSearchResult,
    CatalystSearchResultItem,
    CatalystStockOverview,
)
from src.modules.research.infrastructure.catalyst_context.\
        context_builder import (
            CatalystContextBuilderImpl,
        )


def test_catalyst_context_builder_normal_case():
    builder = CatalystContextBuilderImpl()

    overview = CatalystStockOverview(
        stock_name="TestStock", industry="TestIndustry", third_code="000001.SZ"
    )

    search_results = [
        CatalystSearchResult(
            dimension_topic="公司重大事件与动态",
            items=[
                CatalystSearchResultItem(
                    title="Event 1",
                    url="http://test.com/1",
                    snippet="Snippet 1",
                    site_name="Source 1",
                    published_date="2023-01-01",
                )
            ],
        ),
        CatalystSearchResult(
            dimension_topic="行业催化与竞争格局",
            items=[
                CatalystSearchResultItem(
                    title="Event 2",
                    url="http://test.com/2",
                    snippet="Snippet 2",
                )
            ],
        ),
        CatalystSearchResult(
            dimension_topic="市场情绪与机构动向",
            items=[]  # Empty items
        ),
        # Missing earnings dimension entirely
        # (simulating degradation or logic skip)
    ]

    context = builder.build(overview, search_results)

    assert context.stock_name == "TestStock"
    assert context.industry == "TestIndustry"
    assert context.current_date == date.today().isoformat()

    # Check populated dimensions
    assert "[1] Event 1" in context.company_events_context
    assert "来源: Source 1" in context.company_events_context

    assert "[1] Event 2" in context.industry_catalyst_context

    # Check empty dimensions
    assert "该维度暂无搜索结果，信息有限" in context.market_sentiment_context
    assert "该维度暂无搜索结果，信息有限" in context.earnings_context

    # Check URLs
    assert "http://test.com/1" in context.all_source_urls
    assert "http://test.com/2" in context.all_source_urls


def test_catalyst_context_builder_url_deduplication():
    builder = CatalystContextBuilderImpl()
    overview = CatalystStockOverview(
        stock_name="S", industry="I", third_code="C"
    )

    search_results = [
        CatalystSearchResult(
            dimension_topic="公司重大事件与动态",
            items=[
                CatalystSearchResultItem(
                    title="T1", url="http://dup.com", snippet="S1"
                ),
                CatalystSearchResultItem(
                    title="T2", url="http://dup.com", snippet="S2"
                ),
            ],
        )
    ]

    context = builder.build(overview, search_results)

    # URL only appears once
    assert context.all_source_urls.count("http://dup.com") == 1
