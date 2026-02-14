from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.modules.knowledge_center.domain.dtos.graph_query_dtos import (
    GraphNodeDTO,
    GraphRelationshipDTO,
    StockGraphDTO,
    StockNeighborDTO,
)
from src.modules.knowledge_center.domain.dtos.graph_sync_dtos import SyncResult
from src.modules.knowledge_center.presentation.rest.graph_router import (
    get_graph_service,
    router,
)


@pytest.fixture
def client_and_service() -> tuple[TestClient, AsyncMock]:
    """构造仅挂载 knowledge-graph router 的测试应用，并覆写 GraphService 依赖。"""
    app = FastAPI()
    app.include_router(router)

    service = AsyncMock()

    async def _override_service() -> AsyncMock:
        return service

    app.dependency_overrides[get_graph_service] = _override_service
    return TestClient(app), service


def test_neighbors_endpoint_returns_200(client_and_service: tuple[TestClient, AsyncMock]) -> None:
    """GET neighbors 正常返回 200。"""
    client, service = client_and_service
    service.get_stock_neighbors.return_value = [
        StockNeighborDTO(
            third_code="000002.SZ",
            name="万科A",
            industry="房地产",
            area="深圳",
            market="主板",
            exchange="SZSE",
        )
    ]

    response = client.get(
        "/knowledge-graph/stocks/000001.SZ/neighbors",
        params={"dimension": "industry", "limit": 20},
    )

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert body[0]["third_code"] == "000002.SZ"
    service.get_stock_neighbors.assert_awaited_once_with(
        third_code="000001.SZ",
        dimension="industry",
        limit=20,
    )


def test_neighbors_endpoint_invalid_dimension_returns_422(
    client_and_service: tuple[TestClient, AsyncMock],
) -> None:
    """GET neighbors 传入无效 dimension 返回 422。"""
    client, _ = client_and_service

    response = client.get(
        "/knowledge-graph/stocks/000001.SZ/neighbors",
        params={"dimension": "invalid"},
    )

    assert response.status_code == 422


def test_neighbors_endpoint_missing_dimension_returns_422(
    client_and_service: tuple[TestClient, AsyncMock],
) -> None:
    """GET neighbors 缺少必填参数 dimension 返回 422。"""
    client, _ = client_and_service

    response = client.get("/knowledge-graph/stocks/000001.SZ/neighbors")

    assert response.status_code == 422


def test_graph_endpoint_returns_200(client_and_service: tuple[TestClient, AsyncMock]) -> None:
    """GET graph 正常返回 200。"""
    client, service = client_and_service
    service.get_stock_graph.return_value = StockGraphDTO(
        nodes=[GraphNodeDTO(label="STOCK", id="000001.SZ", properties={"third_code": "000001.SZ"})],
        relationships=[
            GraphRelationshipDTO(
                source_id="000001.SZ",
                target_id="银行",
                relationship_type="BELONGS_TO_INDUSTRY",
            )
        ],
    )

    response = client.get("/knowledge-graph/stocks/000001.SZ/graph", params={"depth": 1})

    assert response.status_code == 200
    body = response.json()
    assert "nodes" in body
    assert "relationships" in body
    service.get_stock_graph.assert_awaited_once_with(third_code="000001.SZ", depth=1)


def test_graph_endpoint_when_stock_not_found_returns_200_null(
    client_and_service: tuple[TestClient, AsyncMock],
) -> None:
    """GET graph 股票不存在时返回 200 且 body 为 null。"""
    client, service = client_and_service
    service.get_stock_graph.return_value = None

    response = client.get("/knowledge-graph/stocks/999999.XX/graph", params={"depth": 1})

    assert response.status_code == 200
    assert response.json() is None


def test_graph_endpoint_invalid_depth_returns_422(
    client_and_service: tuple[TestClient, AsyncMock],
) -> None:
    """GET graph 传入非法 depth（>1）返回 422。"""
    client, _ = client_and_service

    response = client.get("/knowledge-graph/stocks/000001.SZ/graph", params={"depth": 2})

    assert response.status_code == 422


def test_sync_endpoint_returns_200(client_and_service: tuple[TestClient, AsyncMock]) -> None:
    """POST sync 正常返回 200。"""
    client, service = client_and_service
    service.sync_full_graph.return_value = SyncResult(
        total=2,
        success=2,
        failed=0,
        duration_ms=3.0,
        error_details=[],
    )

    response = client.post("/knowledge-graph/sync", json={"mode": "full"})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert body["success"] == 2
    service.sync_full_graph.assert_awaited_once_with(
        include_finance=False,
        batch_size=500,
        skip=0,
        limit=10000,
    )


def test_sync_endpoint_incremental_without_codes_uses_window_mode(
    client_and_service: tuple[TestClient, AsyncMock],
) -> None:
    """POST sync incremental 未传 third_codes 时走自动时间窗口模式。"""
    client, service = client_and_service
    service.sync_incremental_graph.return_value = SyncResult(
        total=3,
        success=3,
        failed=0,
        duration_ms=12.0,
        error_details=[],
    )

    response = client.post(
        "/knowledge-graph/sync",
        json={"mode": "incremental", "window_days": 5, "limit": 500},
    )

    assert response.status_code == 200
    assert response.json()["success"] == 3
    service.sync_incremental_graph.assert_awaited_once_with(
        third_codes=None,
        include_finance=False,
        batch_size=500,
        window_days=5,
        limit=500,
    )


def test_sync_endpoint_missing_mode_returns_422(
    client_and_service: tuple[TestClient, AsyncMock],
) -> None:
    """POST sync 缺少必填字段 mode 返回 422。"""
    client, _ = client_and_service

    response = client.post("/knowledge-graph/sync", json={})

    assert response.status_code == 422
