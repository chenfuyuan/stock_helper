from unittest.mock import AsyncMock

import pytest

from src.modules.knowledge_center.application.queries.get_stock_graph import GetStockGraphQuery
from src.modules.knowledge_center.application.queries.get_stock_neighbors import (
    GetStockNeighborsQuery,
)
from src.modules.knowledge_center.domain.dtos.graph_query_dtos import (
    GraphNodeDTO,
    GraphRelationshipDTO,
    StockGraphDTO,
    StockNeighborDTO,
)


@pytest.mark.asyncio
@pytest.mark.parametrize("dimension", ["industry", "area", "market", "exchange"])
async def test_get_stock_neighbors_supports_all_dimensions(dimension: str) -> None:
    """验证 neighbors 查询支持四种维度并返回正确结果。"""
    repo = AsyncMock()
    expected = [
        StockNeighborDTO(
            third_code="000002.SZ",
            name="万科A",
            industry="房地产",
            area="深圳",
            market="主板",
            exchange="SZSE",
        )
    ]
    repo.find_neighbors.return_value = expected
    query = GetStockNeighborsQuery(graph_repo=repo)

    result = await query.execute(third_code="000001.SZ", dimension=dimension, limit=10)

    assert result == expected
    repo.find_neighbors.assert_awaited_once_with(
        third_code="000001.SZ",
        dimension=dimension,
        limit=10,
    )


@pytest.mark.asyncio
async def test_get_stock_graph_handles_missing_dimension_without_error() -> None:
    """验证个股关系网络在缺失某维度时仍可正常返回其余节点和关系。"""
    repo = AsyncMock()
    repo.find_stock_graph.return_value = StockGraphDTO(
        nodes=[
            GraphNodeDTO(label="STOCK", id="000001.SZ", properties={"third_code": "000001.SZ"}),
            GraphNodeDTO(label="AREA", id="深圳", properties={"name": "深圳"}),
            GraphNodeDTO(label="MARKET", id="主板", properties={"name": "主板"}),
            GraphNodeDTO(label="EXCHANGE", id="SZSE", properties={"name": "SZSE"}),
        ],
        relationships=[
            GraphRelationshipDTO(
                source_id="000001.SZ",
                target_id="深圳",
                relationship_type="LOCATED_IN",
            ),
            GraphRelationshipDTO(
                source_id="000001.SZ",
                target_id="主板",
                relationship_type="TRADES_ON",
            ),
            GraphRelationshipDTO(
                source_id="000001.SZ",
                target_id="SZSE",
                relationship_type="LISTED_ON",
            ),
        ],
    )
    query = GetStockGraphQuery(graph_repo=repo)

    result = await query.execute(third_code="000001.SZ", depth=1)

    assert result is not None
    labels = {n.label for n in result.nodes}
    assert "STOCK" in labels
    assert "INDUSTRY" not in labels
    assert len(result.relationships) == 3
    repo.find_stock_graph.assert_awaited_once_with(third_code="000001.SZ", depth=1)


@pytest.mark.asyncio
async def test_get_stock_neighbors_returns_empty_when_stock_not_found() -> None:
    """股票不存在时，neighbors 查询应返回空列表而非抛异常。"""
    repo = AsyncMock()
    repo.find_neighbors.return_value = []
    query = GetStockNeighborsQuery(graph_repo=repo)

    result = await query.execute(third_code="999999.XX", dimension="industry", limit=20)

    assert result == []
    repo.find_neighbors.assert_awaited_once_with(
        third_code="999999.XX",
        dimension="industry",
        limit=20,
    )


@pytest.mark.asyncio
async def test_get_stock_graph_returns_none_when_stock_not_found() -> None:
    """股票不存在时，graph 查询应返回 None。"""
    repo = AsyncMock()
    repo.find_stock_graph.return_value = None
    query = GetStockGraphQuery(graph_repo=repo)

    result = await query.execute(third_code="999999.XX", depth=1)

    assert result is None
    repo.find_stock_graph.assert_awaited_once_with(third_code="999999.XX", depth=1)
