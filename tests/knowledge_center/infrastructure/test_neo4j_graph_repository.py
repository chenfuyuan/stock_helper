from unittest.mock import MagicMock

import pytest

pytest.importorskip("neo4j")

from src.modules.knowledge_center.domain.dtos.graph_sync_dtos import StockGraphSyncDTO
from src.modules.knowledge_center.domain.dtos.graph_sync_dtos import DimensionDTO
from src.modules.knowledge_center.infrastructure.persistence.neo4j_graph_repository import (
    Neo4jGraphRepository,
)


@pytest.mark.asyncio
async def test_ensure_constraints_runs_five_constraint_cyphers() -> None:
    """验证 ensure_constraints 会执行 5 条唯一约束 Cypher。"""
    session = MagicMock()
    driver = MagicMock()
    driver.session.return_value.__enter__.return_value = session
    repo = Neo4jGraphRepository(driver=driver)

    await repo.ensure_constraints()

    assert session.run.call_count == 5
    cyphers = [call.args[0] for call in session.run.call_args_list]
    assert any("stock_third_code_unique" in q for q in cyphers)
    assert any("industry_name_unique" in q for q in cyphers)
    assert any("area_name_unique" in q for q in cyphers)
    assert any("market_name_unique" in q for q in cyphers)
    assert any("exchange_name_unique" in q for q in cyphers)


@pytest.mark.asyncio
async def test_merge_stocks_uses_unwind_merge_cypher_with_batch_payload() -> None:
    """验证 merge_stocks 通过 UNWIND+MERGE 批量提交并传递 DTO 序列化参数。"""
    session = MagicMock()
    driver = MagicMock()
    driver.session.return_value.__enter__.return_value = session
    repo = Neo4jGraphRepository(driver=driver)

    dto = StockGraphSyncDTO(
        third_code="000001.SZ",
        symbol="000001",
        name="平安银行",
        industry="银行",
        area="深圳",
        market="主板",
        exchange="SZSE",
    )

    result = await repo.merge_stocks(stocks=[dto], batch_size=1)

    assert result.total == 1
    assert result.success == 1
    assert result.failed == 0
    assert session.run.call_count == 1

    cypher = session.run.call_args.args[0]
    params = session.run.call_args.kwargs
    assert "UNWIND $stocks AS stock" in cypher
    assert "MERGE (s:STOCK {third_code: stock.third_code})" in cypher
    assert "BELONGS_TO_INDUSTRY" in cypher
    assert "LOCATED_IN" in cypher
    assert "TRADES_ON" in cypher
    assert "LISTED_ON" in cypher
    assert isinstance(params["stocks"], list)
    assert params["stocks"][0]["third_code"] == "000001.SZ"


@pytest.mark.asyncio
async def test_merge_stocks_full_sync_source_count_matches_payload_count() -> None:
    """验证全量同步时：提交 payload 数量与结果 success/total 一致，且包含维度关系写入语义。"""
    session = MagicMock()
    driver = MagicMock()
    driver.session.return_value.__enter__.return_value = session
    repo = Neo4jGraphRepository(driver=driver)

    stocks = [
        StockGraphSyncDTO(
            third_code="000001.SZ",
            symbol="000001",
            name="平安银行",
            industry="银行",
            area="深圳",
            market="主板",
            exchange="SZSE",
        ),
        StockGraphSyncDTO(
            third_code="000002.SZ",
            symbol="000002",
            name="万科A",
            industry="房地产",
            area="深圳",
            market="主板",
            exchange="SZSE",
        ),
    ]

    result = await repo.merge_stocks(stocks=stocks, batch_size=500)

    assert result.total == 2
    assert result.success == 2
    assert result.failed == 0
    params = session.run.call_args.kwargs
    assert len(params["stocks"]) == 2
    cypher = session.run.call_args.args[0]
    assert "BELONGS_TO_INDUSTRY" in cypher
    assert "LOCATED_IN" in cypher
    assert "TRADES_ON" in cypher
    assert "LISTED_ON" in cypher


@pytest.mark.asyncio
async def test_merge_stocks_is_idempotent_semantics_by_using_merge_not_create() -> None:
    """验证 Cypher 使用 MERGE（而非 CREATE）表达幂等语义。"""
    session = MagicMock()
    driver = MagicMock()
    driver.session.return_value.__enter__.return_value = session
    repo = Neo4jGraphRepository(driver=driver)

    dto = StockGraphSyncDTO(
        third_code="000001.SZ",
        symbol="000001",
        name="平安银行",
        industry="银行",
        area="深圳",
        market="主板",
        exchange="SZSE",
    )

    await repo.merge_stocks(stocks=[dto], batch_size=1)

    cypher = session.run.call_args.args[0]
    assert "MERGE (s:STOCK" in cypher
    assert "MERGE (i:INDUSTRY" in cypher
    assert "MERGE (a:AREA" in cypher
    assert "MERGE (m:MARKET" in cypher
    assert "MERGE (e:EXCHANGE" in cypher
    assert "CREATE (s:STOCK" not in cypher


@pytest.mark.asyncio
async def test_merge_stocks_continues_when_single_batch_fails() -> None:
    """验证单批失败不中断：后续批次继续执行并返回 success/failed 摘要。"""
    session = MagicMock()
    session.run.side_effect = [
        Exception("batch-1 failed"),
        Exception("record-1 failed"),
        None,
    ]
    driver = MagicMock()
    driver.session.return_value.__enter__.return_value = session
    repo = Neo4jGraphRepository(driver=driver)

    stocks = [
        StockGraphSyncDTO(
            third_code="000001.SZ",
            symbol="000001",
            name="平安银行",
        ),
        StockGraphSyncDTO(
            third_code="000002.SZ",
            symbol="000002",
            name="万科A",
        ),
    ]

    result = await repo.merge_stocks(stocks=stocks, batch_size=1)

    assert result.total == 2
    assert result.success == 1
    assert result.failed == 1
    assert len(result.error_details) == 1
    assert "third_code=000001.SZ" in result.error_details[0]


@pytest.mark.asyncio
async def test_merge_dimensions_runs_grouped_merge_for_each_label() -> None:
    """验证 merge_dimensions 会按维度标签分组执行 MERGE。"""
    session = MagicMock()
    driver = MagicMock()
    driver.session.return_value.__enter__.return_value = session
    repo = Neo4jGraphRepository(driver=driver)

    dimensions = [
        DimensionDTO(label="INDUSTRY", name="银行"),
        DimensionDTO(label="AREA", name="深圳"),
        DimensionDTO(label="MARKET", name="主板"),
        DimensionDTO(label="EXCHANGE", name="SZSE"),
    ]

    await repo.merge_dimensions(dimensions)

    assert session.run.call_count == 4
    cyphers = [call.args[0] for call in session.run.call_args_list]
    assert any("MERGE (d:INDUSTRY" in q for q in cyphers)
    assert any("MERGE (d:AREA" in q for q in cyphers)
    assert any("MERGE (d:MARKET" in q for q in cyphers)
    assert any("MERGE (d:EXCHANGE" in q for q in cyphers)
