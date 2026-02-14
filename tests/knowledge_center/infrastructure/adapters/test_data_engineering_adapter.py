from datetime import date
from unittest.mock import AsyncMock

import pytest

from src.modules.data_engineering.domain.model.enums import ExchangeType, ListStatus, MarketType
from src.modules.data_engineering.domain.model.stock import StockInfo
from src.modules.knowledge_center.domain.dtos.graph_sync_dtos import StockGraphSyncDTO
from src.modules.knowledge_center.infrastructure.adapters.data_engineering_adapter import (
    DataEngineeringAdapter,
)


@pytest.mark.asyncio
async def test_fetch_all_stocks_for_sync_returns_only_graph_sync_dto() -> None:
    """验证 Adapter 返回 knowledge_center DTO，不暴露 data_engineering 领域实体。"""
    stock_repo = AsyncMock()
    stock_repo.get_all.return_value = [
        StockInfo(
            third_code="000001.SZ",
            symbol="000001",
            name="平安银行",
            fullname="平安银行股份有限公司",
            list_date=date(1991, 4, 3),
            list_status=ListStatus.LISTED,
            curr_type="CNY",
            industry="银行",
            area="深圳",
            market=MarketType.MAIN,
            exchange=ExchangeType.SZSE,
        )
    ]

    adapter = DataEngineeringAdapter(stock_repo=stock_repo)

    items = await adapter.fetch_all_stocks_for_sync(include_finance=False)

    assert len(items) == 1
    assert isinstance(items[0], StockGraphSyncDTO)
    assert items[0].third_code == "000001.SZ"
    assert items[0].industry == "银行"
    assert items[0].market == "主板"
    assert items[0].exchange == "SZSE"
    assert items[0].list_date == "19910403"


@pytest.mark.asyncio
async def test_fetch_stocks_for_incremental_sync_without_codes_uses_window() -> None:
    """未传 third_codes 时，应基于时间窗口筛选股票并走批量查询转换。"""
    stock_repo = AsyncMock()

    old_stock = StockInfo(
        third_code="000001.SZ",
        symbol="000001",
        name="平安银行",
        list_status=ListStatus.LISTED,
        market=MarketType.MAIN,
        exchange=ExchangeType.SZSE,
        last_finance_sync_date=date(2020, 1, 1),
    )
    recent_stock = StockInfo(
        third_code="000002.SZ",
        symbol="000002",
        name="万科A",
        list_status=ListStatus.LISTED,
        market=MarketType.MAIN,
        exchange=ExchangeType.SZSE,
        last_finance_sync_date=date.today(),
    )
    unknown_stock = StockInfo(
        third_code="000003.SZ",
        symbol="000003",
        name="国农科技",
        list_status=ListStatus.LISTED,
        market=MarketType.MAIN,
        exchange=ExchangeType.SZSE,
        last_finance_sync_date=None,
    )

    stock_repo.get_all.return_value = [old_stock, recent_stock, unknown_stock]
    stock_repo.get_by_third_codes.return_value = [recent_stock, unknown_stock]

    adapter = DataEngineeringAdapter(stock_repo=stock_repo)

    items = await adapter.fetch_stocks_for_incremental_sync(
        third_codes=None,
        include_finance=False,
        window_days=3,
        limit=100,
    )

    assert len(items) == 2
    assert {item.third_code for item in items} == {"000002.SZ", "000003.SZ"}
    stock_repo.get_all.assert_awaited_once_with(skip=0, limit=100)
    stock_repo.get_by_third_codes.assert_awaited_once_with(["000002.SZ", "000003.SZ"])
