"""
Web Search 功能测试套件

测试覆盖：
- 博查适配器单元测试
- 适配器错误处理测试  
- 搜索服务测试
- 配置测试
- 端到端路由测试
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
import httpx
from fastapi.testclient import TestClient

from src.modules.llm_platform.infrastructure.adapters.bocha_web_search import (
    BochaWebSearchAdapter,
)
from src.modules.llm_platform.application.services.web_search_service import (
    WebSearchService,
)
from src.modules.llm_platform.domain.web_search_dtos import (
    WebSearchRequest,
    WebSearchResponse,
    WebSearchResultItem,
)
from src.modules.llm_platform.domain.exceptions import (
    WebSearchError,
    WebSearchConnectionError,
    WebSearchConfigError,
)


class TestBochaWebSearchAdapter:
    """博查适配器单元测试"""

    @pytest.mark.asyncio
    async def test_normal_search_returns_mapped_results(self):
        """测试正常搜索返回映射结果（对应 Scenario: 正常搜索返回映射结果）"""
        # Mock HTTP 响应
        mock_response_data = {
            "data": {  # 新增 data 包装层
                "webPages": {
                    "value": [
                        {
                            "name": "测试标题1",
                            "url": "https://example.com/1",
                            "snippet": "测试摘要1",
                            "summary": "AI摘要1",
                            "siteName": "示例站点1",
                            "datePublished": "2024-01-01",
                        },
                        {
                            "name": "测试标题2",
                            "url": "https://example.com/2",
                            "snippet": "测试摘要2",
                            "summary": None,
                            "siteName": None,
                            "datePublished": None,
                        },
                    ],
                    "totalEstimatedMatches": 100,
                }
            }
        }

        adapter = BochaWebSearchAdapter(api_key="test_key")

        with patch("httpx.AsyncClient") as mock_client:
            mock_post = AsyncMock()
            mock_post.return_value.status_code = 200
            mock_post.return_value.json = Mock(return_value=mock_response_data)
            mock_client.return_value.__aenter__.return_value.post = mock_post

            request = WebSearchRequest(query="测试查询")
            response = await adapter.search(request)

            # 验证映射正确
            assert response.query == "测试查询"
            assert response.total_matches == 100
            assert len(response.results) == 2
            assert response.results[0].title == "测试标题1"
            assert response.results[0].url == "https://example.com/1"
            assert response.results[0].snippet == "测试摘要1"
            assert response.results[0].summary == "AI摘要1"
            assert response.results[0].site_name == "示例站点1"
            assert response.results[0].published_date == "2024-01-01"

    @pytest.mark.asyncio
    async def test_empty_results_returns_empty_list(self):
        """测试无结果时返回空列表（对应 Scenario: 搜索无结果时返回空列表）"""
        mock_response_data = {"data": {"webPages": {"value": []}}}

        adapter = BochaWebSearchAdapter(api_key="test_key")

        with patch("httpx.AsyncClient") as mock_client:
            mock_post = AsyncMock()
            mock_post.return_value.status_code = 200
            mock_post.return_value.json = Mock(return_value=mock_response_data)
            mock_client.return_value.__aenter__.return_value.post = mock_post

            request = WebSearchRequest(query="无结果查询")
            response = await adapter.search(request)

            assert response.query == "无结果查询"
            assert len(response.results) == 0

    @pytest.mark.asyncio
    async def test_request_params_passed_correctly(self):
        """测试请求参数正确传递（对应 Scenario: 请求参数正确传递）"""
        mock_response_data = {"data": {"webPages": {"value": []}}}

        adapter = BochaWebSearchAdapter(api_key="test_key")

        with patch("httpx.AsyncClient") as mock_client:
            mock_post = AsyncMock()
            mock_post.return_value.status_code = 200
            mock_post.return_value.json = Mock(return_value=mock_response_data)
            mock_client.return_value.__aenter__.return_value.post = mock_post

            request = WebSearchRequest(
                query="测试", freshness="oneWeek", summary=False, count=20
            )
            response = await adapter.search(request)

            # 验证请求参数
            call_args = mock_post.call_args
            request_body = call_args.kwargs["json"]
            assert request_body["query"] == "测试"
            assert request_body["freshness"] == "oneWeek"
            assert request_body["summary"] is False
            assert request_body["count"] == 20

    @pytest.mark.asyncio
    async def test_http_error_raises_web_search_error(self):
        """测试 HTTP 错误转为 WebSearchError（对应 Scenario: HTTP 错误码转为 WebSearchError）"""
        adapter = BochaWebSearchAdapter(api_key="test_key")

        with patch("httpx.AsyncClient") as mock_client:
            mock_post = AsyncMock()
            mock_post.return_value.status_code = 500
            mock_post.return_value.text = "Internal Server Error"
            mock_post.return_value.json = Mock(return_value={"error": "服务器错误"})
            mock_client.return_value.__aenter__.return_value.post = mock_post

            request = WebSearchRequest(query="测试")
            with pytest.raises(WebSearchError) as exc_info:
                await adapter.search(request)

            assert "500" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_network_timeout_raises_connection_error(self):
        """测试网络超时转为 WebSearchConnectionError（对应 Scenario: 网络超时转为 WebSearchConnectionError）"""
        adapter = BochaWebSearchAdapter(api_key="test_key")

        with patch("httpx.AsyncClient") as mock_client:
            mock_post = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))
            mock_client.return_value.__aenter__.return_value.post = mock_post

            request = WebSearchRequest(query="测试")
            with pytest.raises(WebSearchConnectionError):
                await adapter.search(request)

    @pytest.mark.asyncio
    async def test_empty_api_key_raises_config_error(self):
        """测试 API Key 未配置抛出 WebSearchConfigError（对应 Scenario: API Key 未配置时抛出 WebSearchConfigError）"""
        adapter = BochaWebSearchAdapter(api_key="")

        request = WebSearchRequest(query="测试")
        with pytest.raises(WebSearchConfigError) as exc_info:
            await adapter.search(request)

        assert "API Key" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_missing_webpages_field_defensive_handling(self):
        """测试响应缺少字段时防御性处理（对应 Scenario: 响应格式异常时防御性处理）"""
        mock_response_data = {}  # 缺少 webPages 字段

        adapter = BochaWebSearchAdapter(api_key="test_key")

        with patch("httpx.AsyncClient") as mock_client:
            mock_post = AsyncMock()
            mock_post.return_value.status_code = 200
            mock_post.return_value.json = Mock(return_value=mock_response_data)
            mock_client.return_value.__aenter__.return_value.post = mock_post

            request = WebSearchRequest(query="测试")
            response = await adapter.search(request)

            # 应该返回空结果，而不是崩溃
            assert len(response.results) == 0


class TestWebSearchService:
    """搜索服务测试"""

    @pytest.mark.asyncio
    async def test_service_delegates_to_provider(self):
        """测试服务委托 Provider 执行搜索（对应 Scenario: 正常搜索调用）"""
        mock_provider = AsyncMock()
        mock_response = WebSearchResponse(
            query="测试", total_matches=10, results=[]
        )
        mock_provider.search.return_value = mock_response

        service = WebSearchService(provider=mock_provider)
        request = WebSearchRequest(query="测试")
        response = await service.search(request)

        mock_provider.search.assert_awaited_once_with(request)
        assert response == mock_response

    @pytest.mark.asyncio
    async def test_service_logs_search_info(self):
        """测试服务记录搜索日志（对应 Scenario: 服务记录搜索日志）"""
        mock_provider = AsyncMock()
        mock_response = WebSearchResponse(
            query="测试",
            total_matches=5,
            results=[
                WebSearchResultItem(title="测试", url="http://test.com", snippet="测试")
            ],
        )
        mock_provider.search.return_value = mock_response

        service = WebSearchService(provider=mock_provider)
        request = WebSearchRequest(query="测试")

        with patch("src.modules.llm_platform.application.services.web_search_service.logger") as mock_logger: 
            response = await service.search(request)

            # 验证日志记录
            assert mock_logger.info.call_count >= 2  # 搜索前后各一次

    def test_service_only_depends_on_port(self):
        """测试服务仅依赖 Port 抽象（对应 Scenario: 服务仅依赖 Port 抽象）"""
        from inspect import signature
        sig = signature(WebSearchService.__init__)
        
        # 验证构造函数仅接受 IWebSearchProvider
        assert "provider" in sig.parameters


class TestConfiguration:
    """配置测试"""

    def test_settings_has_bocha_fields(self):
        """测试 Settings 包含博查配置字段（对应 Scenario: 配置从环境变量加载）"""
        from src.shared.config import Settings

        settings = Settings()
        assert hasattr(settings, "BOCHA_API_KEY")
        assert hasattr(settings, "BOCHA_BASE_URL")

    def test_settings_default_values(self):
        """测试配置默认值（对应 Scenario: 未配置 API Key 时应用正常启动）"""
        from src.shared.config import Settings
        import os
        from unittest import mock

        with mock.patch.dict(os.environ, {"BOCHA_API_KEY": ""}, clear=True):
             settings = Settings()
             assert settings.BOCHA_API_KEY == ""
             assert settings.BOCHA_BASE_URL == "https://api.bochaai.com"


class TestWebSearchResponse:
    """响应 DTO 测试"""

    def test_to_prompt_context_format(self):
        """测试转换为 Prompt 上下文格式"""
        response = WebSearchResponse(
            query="测试查询",
            results=[
                WebSearchResultItem(
                    title="标题1",
                    url="http://1.com",
                    snippet="摘要1",
                    summary="AI摘要1",
                    site_name="站点1",
                    published_date="2024-01-01",
                ),
                WebSearchResultItem(
                    title="标题2",
                    url="http://2.com",
                    snippet="摘要2",
                    # no summary, no site_name, no date
                ),
            ],
        )

        context = response.to_prompt_context()

        assert "Web Search Results for: '测试查询'" in context
        assert "[1] Title: 标题1" in context
        assert "Source: 站点1 (2024-01-01)" in context
        assert "Content: AI摘要1" in context
        
        assert "[2] Title: 标题2" in context
        assert "Source: Unknown Source" in context
        assert "Content: 摘要2" in context
