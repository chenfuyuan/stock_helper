"""
为 GetDailyBarsByDateUseCase 编写单元测试。
验证按日期查询全市场日线数据的功能。
"""

from datetime import date
from unittest.mock import AsyncMock

import pytest

from src.modules.data_engineering.application.queries.get_daily_bars_by_date import (
    DailyBarDTO,
    GetDailyBarsByDateUseCase,
)
from src.modules.data_engineering.domain.model.stock_daily import StockDaily


@pytest.mark.asyncio
async def test_get_daily_bars_by_date_returns_dto_list():
    """调用按日期查询全市场日线接口，断言返回 DTO 列表。"""
    trade_date = date(2025, 1, 6)

    mock_daily_1 = StockDaily(
        third_code="000001.SZ",
        trade_date=trade_date,
        open=10.0,
        high=11.0,
        low=9.5,
        close=10.5,
        pre_close=10.0,
        change=0.5,
        pct_chg=5.0,
        vol=1000000.0,
        amount=10500000.0,
    )
    mock_daily_2 = StockDaily(
        third_code="600519.SH",
        trade_date=trade_date,
        open=1800.0,
        high=1850.0,
        low=1790.0,
        close=1820.0,
        pre_close=1800.0,
        change=20.0,
        pct_chg=1.11,
        vol=500000.0,
        amount=910000000.0,
    )

    mock_repo = AsyncMock()
    mock_repo.get_all_by_trade_date.return_value = [mock_daily_1, mock_daily_2]

    use_case = GetDailyBarsByDateUseCase(mock_repo)
    result = await use_case.execute(trade_date=trade_date)

    assert isinstance(result, list)
    assert len(result) == 2
    
    for bar in result:
        assert isinstance(bar, DailyBarDTO)
        assert hasattr(bar, "third_code")
        assert hasattr(bar, "trade_date")
        assert hasattr(bar, "open")
        assert hasattr(bar, "high")
        assert hasattr(bar, "low")
        assert hasattr(bar, "close")
        assert hasattr(bar, "vol")
        assert hasattr(bar, "amount")
        assert hasattr(bar, "pct_chg")

    assert result[0].third_code == "000001.SZ"
    assert result[0].pct_chg == 5.0
    assert result[1].third_code == "600519.SH"
    assert result[1].pct_chg == 1.11


@pytest.mark.asyncio
async def test_get_daily_bars_by_date_returns_empty_for_non_trading_day():
    """非交易日查询应返回空列表。"""
    trade_date = date(2025, 1, 4)

    mock_repo = AsyncMock()
    mock_repo.get_all_by_trade_date.return_value = []

    use_case = GetDailyBarsByDateUseCase(mock_repo)
    result = await use_case.execute(trade_date=trade_date)

    assert isinstance(result, list)
    assert len(result) == 0
