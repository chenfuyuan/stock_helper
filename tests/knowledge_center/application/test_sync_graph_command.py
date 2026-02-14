from unittest.mock import AsyncMock

import pytest

from src.modules.knowledge_center.application.commands.sync_graph_command import (
    SyncGraphCommand,
)
from src.modules.knowledge_center.domain.dtos.graph_sync_dtos import (
    StockGraphSyncDTO,
    SyncResult,
)


def _build_sync_dto(code: str) -> StockGraphSyncDTO:
    return StockGraphSyncDTO(
        third_code=code,
        symbol=code.split(".")[0],
        name=f"股票-{code}",
        industry="银行",
        area="深圳",
        market="主板",
        exchange="SZSE",
    )


@pytest.mark.asyncio
async def test_execute_full_sync_uses_source_count_and_calls_repo() -> None:
    """全量同步应按源数据数量写入，并先创建约束后批量写入。"""
    graph_repo = AsyncMock()
    data_adapter = AsyncMock()
    command = SyncGraphCommand(graph_repo=graph_repo, data_adapter=data_adapter)

    stocks = [_build_sync_dto("000001.SZ"), _build_sync_dto("000002.SZ")]
    data_adapter.fetch_all_stocks_for_sync.return_value = stocks
    graph_repo.merge_stocks.return_value = SyncResult(
        total=2,
        success=2,
        failed=0,
        duration_ms=10.0,
        error_details=[],
    )

    result = await command.execute_full_sync(batch_size=500)

    assert result.total == 2
    assert result.success == 2
    data_adapter.fetch_all_stocks_for_sync.assert_awaited_once()
    graph_repo.ensure_constraints.assert_awaited_once()
    graph_repo.merge_stocks.assert_awaited_once_with(stocks=stocks, batch_size=500)


@pytest.mark.asyncio
async def test_execute_incremental_sync_only_syncs_given_codes() -> None:
    """增量同步仅拉取并写入指定 third_codes。"""
    graph_repo = AsyncMock()
    data_adapter = AsyncMock()
    command = SyncGraphCommand(graph_repo=graph_repo, data_adapter=data_adapter)

    target_codes = ["000001.SZ"]
    stocks = [_build_sync_dto("000001.SZ")]
    data_adapter.fetch_stocks_for_incremental_sync.return_value = stocks
    graph_repo.merge_stocks.return_value = SyncResult(
        total=1,
        success=1,
        failed=0,
        duration_ms=5.0,
        error_details=[],
    )

    result = await command.execute_incremental_sync(third_codes=target_codes, batch_size=200)

    assert result.total == 1
    data_adapter.fetch_stocks_for_incremental_sync.assert_awaited_once_with(
        third_codes=target_codes,
        include_finance=False,
        window_days=3,
        limit=10000,
    )
    graph_repo.ensure_constraints.assert_awaited_once()
    graph_repo.merge_stocks.assert_awaited_once_with(stocks=stocks, batch_size=200)


@pytest.mark.asyncio
async def test_execute_incremental_sync_without_codes_uses_window_mode() -> None:
    """增量同步未传 third_codes 时，应按时间窗口模式获取数据并写入。"""
    graph_repo = AsyncMock()
    data_adapter = AsyncMock()
    command = SyncGraphCommand(graph_repo=graph_repo, data_adapter=data_adapter)

    stocks = [_build_sync_dto("000001.SZ")]
    data_adapter.fetch_stocks_for_incremental_sync.return_value = stocks
    graph_repo.merge_stocks.return_value = SyncResult(
        total=1,
        success=1,
        failed=0,
        duration_ms=8.0,
        error_details=[],
    )

    result = await command.execute_incremental_sync(
        third_codes=None,
        batch_size=300,
        window_days=5,
        limit=888,
    )

    assert result.success == 1
    data_adapter.fetch_stocks_for_incremental_sync.assert_awaited_once_with(
        third_codes=None,
        include_finance=False,
        window_days=5,
        limit=888,
    )
    graph_repo.ensure_constraints.assert_awaited_once()
    graph_repo.merge_stocks.assert_awaited_once_with(stocks=stocks, batch_size=300)
