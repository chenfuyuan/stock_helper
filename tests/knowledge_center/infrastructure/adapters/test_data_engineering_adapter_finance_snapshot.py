from datetime import date
from unittest.mock import AsyncMock

import pytest

from src.modules.data_engineering.domain.model.enums import ExchangeType, ListStatus, MarketType
from src.modules.data_engineering.domain.model.stock import StockInfo
from src.modules.knowledge_center.infrastructure.adapters.data_engineering_adapter import (
    DataEngineeringAdapter,
)


@pytest.mark.asyncio
async def test_fetch_all_stocks_for_sync_finance_snapshot_uses_latest_record() -> None:
    """验证开启财务同步时，Stock DTO 财务属性映射为最新一期财务快照。"""
    stock_repo = AsyncMock()
    stock_repo.get_all.return_value = [
        StockInfo(
            third_code="000001.SZ",
            symbol="000001",
            name="平安银行",
            list_date=date(1991, 4, 3),
            list_status=ListStatus.LISTED,
            market=MarketType.MAIN,
            exchange=ExchangeType.SZSE,
            industry="银行",
            area="深圳",
            curr_type="CNY",
        )
    ]

    finance_use_case = AsyncMock()
    finance_use_case.execute.return_value = [
        AsyncMock(
            roe_waa=15.2,
            gross_margin=31.1,
            debt_to_assets=43.5,
            roa=1.8,
        )
    ]

    adapter = DataEngineeringAdapter(
        stock_repo=stock_repo,
        get_finance_use_case=finance_use_case,
    )

    items = await adapter.fetch_all_stocks_for_sync(include_finance=True)

    assert len(items) == 1
    dto = items[0]
    assert dto.roe == 15.2
    assert dto.roa == 1.8
    assert dto.gross_margin == 31.1
    assert dto.debt_to_assets == 43.5
    assert dto.pe_ttm is None
    assert dto.pb is None
    assert dto.total_mv is None
