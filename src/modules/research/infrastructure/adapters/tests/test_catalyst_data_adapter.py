"""
CatalystDataAdapter 单元测试。

mock WebSearchService，断言搜索使用配置中的 count/freshness、结果经过过滤后返回。
"""
import pytest
from unittest.mock import AsyncMock, Mock
from datetime import date

from src.modules.llm_platform.domain.web_search_dtos import WebSearchRequest, WebSearchResponse, WebSearchResultItem
from src.modules.research.infrastructure.adapters.catalyst_data_adapter import CatalystDataAdapter
from src.modules.research.infrastructure.search_utils.result_filter import SearchResultFilter


class TestCatalystDataAdapter:
    @pytest.fixture
    def mock_stock_info_usecase(self):
        """模拟股票信息查询用例"""
        usecase = AsyncMock()
        # 模拟返回股票基础信息
        mock_result = Mock()
        mock_result.info.name = "平安银行"
        mock_result.info.industry = "银行"
        mock_result.daily.third_code = "000001.SZ"
        usecase.execute.return_value = mock_result
        return usecase

    @pytest.fixture
    def mock_web_search_service(self):
        """模拟 Web 搜索服务"""
        service = AsyncMock()
        return service

    @pytest.fixture
    def result_filter(self):
        """搜索结果过滤器"""
        return SearchResultFilter()

    @pytest.fixture
    def adapter(self, mock_stock_info_usecase, mock_web_search_service, result_filter):
        """CatalystDataAdapter 实例"""
        return CatalystDataAdapter(
            stock_info_use_case=mock_stock_info_usecase,
            web_search_service=mock_web_search_service,
            result_filter=result_filter,
        )

    async def test_search_catalyst_context_uses_config_parameters(self, adapter, mock_web_search_service):
        """测试搜索使用配置中的 count/freshness 参数"""
        # 模拟搜索响应
        mock_items = [
            WebSearchResultItem(
                title="公司并购新闻",
                url="https://example.com/news1",
                snippet="平安银行并购",
                summary="平安银行宣布收购某金融科技公司",
                site_name="财经网",
                published_date="2024-01-15",
            ),
            WebSearchResultItem(
                title="行业催化新闻",
                url="https://example.com/news2",
                snippet="银行业政策",
                summary="银保监会发布银行业新政策",
                site_name="监管网",
                published_date="2024-01-14",
            ),
        ]
        mock_response = WebSearchResponse(query="测试查询", results=mock_items)
        mock_web_search_service.search.return_value = mock_response

        # 执行搜索
        results = await adapter.search_catalyst_context(stock_name="平安银行", industry="银行")

        # 验证搜索调用次数（4 个维度）
        assert mock_web_search_service.search.call_count == 4

        # 验证每个搜索请求使用了正确的参数
        calls = mock_web_search_service.search.call_args_list
        for call in calls:
            request = call[0][0]  # 第一个位置参数是 WebSearchRequest
            assert isinstance(request, WebSearchRequest)
            # 验证 count 在 4-10 范围内
            assert 4 <= request.count <= 10
            # 验证 freshness 是合法值
            assert request.freshness in ["oneDay", "oneWeek", "oneMonth", "oneYear", "noLimit"]
            # 验证启用了摘要
            assert request.summary is True

        # 验证返回结果数量（4 个维度）
        assert len(results) == 4

        # 验证每个结果都有维度主题
        for result in results:
            assert hasattr(result, 'dimension_topic')
            assert hasattr(result, 'items')

    async def test_search_catalyst_context_filters_results(self, adapter, mock_web_search_service):
        """测试搜索结果经过过滤后返回"""
        # 模拟包含噪音的搜索响应
        mock_items = [
            WebSearchResultItem(
                title="有效催化1",
                url="https://example.com/news1",
                snippet="有摘要",
                summary="有AI摘要",
                site_name="财经网",
                published_date="2024-01-15",
            ),
            WebSearchResultItem(
                title="",  # 空标题，应被过滤
                url="https://example.com/news2",
                snippet="无标题",
                summary="无标题内容",
                site_name="财经网",
                published_date="2024-01-14",
            ),
            WebSearchResultItem(
                title="无内容",
                url="https://example.com/news3",
                snippet="",  # 空 snippet
                summary="",  # 空 summary
                site_name="财经网",
                published_date="2024-01-13",
            ),
            WebSearchResultItem(
                title="有效催化2",
                url="https://example.com/news1",  # 重复 URL，应被去重
                snippet="重复URL",
                summary="重复内容",
                site_name="财经网",
                published_date="2024-01-12",
            ),
        ]
        mock_response = WebSearchResponse(query="测试查询", results=mock_items)
        mock_web_search_service.search.return_value = mock_response

        # 执行搜索
        results = await adapter.search_catalyst_context(stock_name="平安银行", industry="银行")

        # 验证过滤后的结果
        # 应该只有 2 个有效条目（有效催化1 和有效催化2，后者因 URL 重复被去重）
        # 但由于是 4 个维度，每个维度都会收到相同的 mock_items
        # 所以每个维度过滤后应该是 1 个有效条目
        for result in results:
            assert len(result.items) == 1  # 每个维度过滤后只有 1 个有效条目
            assert result.items[0].title == "有效催化1"  # 保留第一个有效条目

    async def test_search_catalyst_context_handles_search_errors(self, adapter, mock_web_search_service):
        """测试搜索错误处理"""
        # 模拟搜索服务抛出异常
        mock_web_search_service.search.side_effect = Exception("搜索服务错误")

        # 执行搜索
        results = await adapter.search_catalyst_context(stock_name="平安银行", industry="银行")

        # 验证错误处理：所有维度返回空结果
        assert len(results) == 4
        for result in results:
            assert len(result.items) == 0
            assert hasattr(result, 'dimension_topic')

    async def test_get_stock_overview_success(self, adapter, mock_stock_info_usecase):
        """测试获取股票概览成功"""
        # 执行获取
        overview = await adapter.get_stock_overview("000001.SZ")

        # 验证调用
        mock_stock_info_usecase.execute.assert_called_once_with("000001.SZ")

        # 验证返回结果
        assert overview is not None
        assert overview.stock_name == "平安银行"
        assert overview.industry == "银行"
        assert overview.third_code == "000001.SZ"

    async def test_get_stock_overview_not_found(self, adapter, mock_stock_info_usecase):
        """测试股票不存在"""
        # 模拟返回 None
        mock_stock_info_usecase.execute.return_value = None

        # 执行获取
        overview = await adapter.get_stock_overview("INVALID.SZ")

        # 验证返回 None
        assert overview is None

    async def test_search_catalyst_context_queries_contain_stock_name(self, adapter, mock_web_search_service):
        """测试所有维度查询都包含 stock_name"""
        mock_response = WebSearchResponse(query="测试查询", results=[])
        mock_web_search_service.search.return_value = mock_response

        # 执行搜索
        await adapter.search_catalyst_context(stock_name="平安银行", industry="银行")

        # 验证每个搜索查询都包含 "平安银行"
        calls = mock_web_search_service.search.call_args_list
        for call in calls:
            request = call[0][0]
            assert "平安银行" in request.query
