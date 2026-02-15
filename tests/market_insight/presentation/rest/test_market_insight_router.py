"""
MarketInsightRouter REST API 集成测试
验证 GET/POST 请求、参数校验、空数据场景
"""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.modules.market_insight.application.dtos.market_insight_dtos import (
    ConceptHeatDTO,
    DailyReportResult,
    LimitUpStockDTO,
)


@pytest.fixture
def client():
    """测试客户端"""
    return TestClient(app)


@pytest.fixture
def mock_container():
    """Mock MarketInsightContainer"""
    container = MagicMock()
    
    # Mock queries
    concept_heat_query = AsyncMock()
    limit_up_query = AsyncMock()
    
    # Mock command
    generate_daily_report_cmd = AsyncMock()
    
    container.get_concept_heat_query.return_value = concept_heat_query
    container.get_limit_up_query.return_value = limit_up_query
    container.get_generate_daily_report_cmd.return_value = generate_daily_report_cmd
    
    return container


def test_get_concept_heat_success(client, mock_container):
    """GET /api/market-insight/concept-heat 成功场景"""
    
    mock_query = mock_container.get_concept_heat_query.return_value
    mock_query.execute.return_value = [
        ConceptHeatDTO(
            trade_date=date(2025, 1, 6),
            concept_code="BK0001",
            concept_name="人工智能",
            avg_pct_chg=5.5,
            stock_count=50,
            up_count=45,
            down_count=5,
            limit_up_count=10,
            total_amount=5000000000.0,
        ),
    ]
    
    with patch(
        "src.modules.market_insight.presentation.rest.market_insight_router.get_container",
        return_value=mock_container,
    ):
        response = client.get(
            "/api/market-insight/concept-heat",
            params={"trade_date": "2025-01-06", "top_n": 10},
        )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["concept_code"] == "BK0001"
    assert data[0]["concept_name"] == "人工智能"
    assert data[0]["avg_pct_chg"] == 5.5


def test_get_concept_heat_missing_trade_date(client):
    """GET /api/market-insight/concept-heat 缺少必填参数"""
    
    response = client.get("/api/market-insight/concept-heat")
    
    assert response.status_code == 422


def test_get_concept_heat_empty_result(client, mock_container):
    """GET /api/market-insight/concept-heat 空数据场景"""
    
    mock_query = mock_container.get_concept_heat_query.return_value
    mock_query.execute.return_value = []
    
    with patch(
        "src.modules.market_insight.presentation.rest.market_insight_router.get_container",
        return_value=mock_container,
    ):
        response = client.get(
            "/api/market-insight/concept-heat",
            params={"trade_date": "2025-01-04", "top_n": 10},
        )
    
    assert response.status_code == 200
    assert response.json() == []


def test_get_limit_up_success(client, mock_container):
    """GET /api/market-insight/limit-up 成功场景"""
    
    mock_query = mock_container.get_limit_up_query.return_value
    mock_query.execute.return_value = [
        LimitUpStockDTO(
            trade_date=date(2025, 1, 6),
            third_code="000001.SZ",
            stock_name="平安银行",
            pct_chg=10.01,
            close=12.0,
            amount=200000000.0,
            concept_codes=["BK0001"],
            concept_names=["金融概念"],
            limit_type="MAIN_BOARD",
        ),
    ]
    
    with patch(
        "src.modules.market_insight.presentation.rest.market_insight_router.get_container",
        return_value=mock_container,
    ):
        response = client.get(
            "/api/market-insight/limit-up",
            params={"trade_date": "2025-01-06"},
        )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["third_code"] == "000001.SZ"
    assert data[0]["stock_name"] == "平安银行"


def test_get_limit_up_with_concept_filter(client, mock_container):
    """GET /api/market-insight/limit-up 按概念过滤"""
    
    mock_query = mock_container.get_limit_up_query.return_value
    mock_query.execute.return_value = []
    
    with patch(
        "src.modules.market_insight.presentation.rest.market_insight_router.get_container",
        return_value=mock_container,
    ):
        response = client.get(
            "/api/market-insight/limit-up",
            params={"trade_date": "2025-01-06", "concept_code": "BK0493"},
        )
    
    assert response.status_code == 200
    mock_query.execute.assert_called_once()
    call_args = mock_query.execute.call_args
    assert call_args[0][1] == "BK0493"


def test_post_daily_report_success(client, mock_container):
    """POST /api/market-insight/daily-report 成功场景"""
    
    mock_cmd = mock_container.get_generate_daily_report_cmd.return_value
    mock_cmd.execute.return_value = DailyReportResult(
        trade_date=date(2025, 1, 6),
        concept_count=320,
        limit_up_count=45,
        report_path="reports/2025-01-06-market-insight.md",
        elapsed_seconds=5.23,
    )
    
    with patch(
        "src.modules.market_insight.presentation.rest.market_insight_router.get_container",
        return_value=mock_container,
    ):
        response = client.post(
            "/api/market-insight/daily-report",
            params={"trade_date": "2025-01-06"},
        )
    
    assert response.status_code == 200
    data = response.json()
    assert data["trade_date"] == "2025-01-06"
    assert data["concept_count"] == 320
    assert data["limit_up_count"] == 45
    assert data["elapsed_seconds"] == 5.23


def test_post_daily_report_missing_trade_date(client):
    """POST /api/market-insight/daily-report 缺少必填参数"""
    
    response = client.post("/api/market-insight/daily-report")
    
    assert response.status_code == 422
