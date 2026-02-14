"""
端到端路由测试 — Web Search API

测试覆盖：
- 正常搜索返回 200
- query 缺失返回 422
- API Key 未配置返回 503
- 连接失败返回 503
- 上游错误返回 502
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.modules.llm_platform.domain.exceptions import (
    WebSearchConfigError,
    WebSearchConnectionError,
    WebSearchError,
)
from src.modules.llm_platform.domain.web_search_dtos import (
    WebSearchResponse,
    WebSearchResultItem,
)


class TestWebSearchRoutes:
    """端到端路由测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        return TestClient(app)

    def test_normal_search_returns_200(self, client):
        """测试正常搜索返回 200（对应 Scenario: 正常搜索请求返回 200）"""
        mock_response = WebSearchResponse(
            query="测试查询",
            total_matches=5,
            results=[
                WebSearchResultItem(
                    title="测试标题",
                    url="https://example.com",
                    snippet="测试摘要",
                    summary="AI摘要",
                    site_name="示例站点",
                    published_date="2024-01-01",
                )
            ],
        )

        with patch(
            "src.modules.llm_platform.presentation.rest.search_routes.get_web_search_service"
        ) as mock_get_service:
            mock_service = Mock()
            mock_service.search = AsyncMock(return_value=mock_response)
            mock_get_service.return_value = mock_service

            response = client.post(
                "/api/v1/llm-platform/web-search/",
                json={"query": "测试查询"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["query"] == "测试查询"
            assert data["total_matches"] == 5
            assert len(data["results"]) == 1
            assert data["results"][0]["title"] == "测试标题"

    def test_missing_query_returns_422(self, client):
        """测试 query 缺失返回 422（对应 Scenario: query 缺失时返回 422）"""
        response = client.post(
            "/api/v1/llm-platform/web-search/",
            json={},  # 缺少 query
        )

        assert response.status_code == 422

    def test_config_error_returns_503(self, client):
        """测试配置错误返回 503（对应 Scenario: API Key 未配置时返回 503）"""
        with patch(
            "src.modules.llm_platform.presentation.rest.search_routes.get_web_search_service"
        ) as mock_get_service:
            mock_service = Mock()
            mock_service.search = AsyncMock(side_effect=WebSearchConfigError("API Key 未配置"))
            mock_get_service.return_value = mock_service

            response = client.post(
                "/api/v1/llm-platform/web-search/",
                json={"query": "测试"},
            )

            assert response.status_code == 503
            assert "API Key" in response.json()["detail"]

    def test_connection_error_returns_503(self, client):
        """测试连接失败返回 503（对应 Scenario: 博查 API 不可用时返回 503）"""
        with patch(
            "src.modules.llm_platform.presentation.rest.search_routes.get_web_search_service"
        ) as mock_get_service:
            mock_service = Mock()
            mock_service.search = AsyncMock(side_effect=WebSearchConnectionError("网络连接失败"))
            mock_get_service.return_value = mock_service

            response = client.post(
                "/api/v1/llm-platform/web-search/",
                json={"query": "测试"},
            )

            assert response.status_code == 503

    def test_api_error_returns_502(self, client):
        """测试上游 API 错误返回 502（对应 Scenario: 博查 API 返回错误时返回 502）"""
        with patch(
            "src.modules.llm_platform.presentation.rest.search_routes.get_web_search_service"
        ) as mock_get_service:
            mock_service = Mock()
            mock_service.search = AsyncMock(side_effect=WebSearchError("上游 API 错误"))
            mock_get_service.return_value = mock_service

            response = client.post(
                "/api/v1/llm-platform/web-search/",
                json={"query": "测试"},
            )

            assert response.status_code == 502
