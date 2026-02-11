"""
Task 1.1 Red：日线查询 Application 接口的测试。
给定 ticker 与日期区间，调用 data_engineering 的日线查询接口，断言返回 DTO 列表且含开高低收量等字段。
先不实现接口时本测试应失败（ImportError 或用例不存在）。
"""
import pytest
from datetime import date
from unittest.mock import AsyncMock

from src.modules.data_engineering.application.queries.get_daily_bars_for_ticker import (
    GetDailyBarsForTickerUseCase,
    DailyBarDTO,
)


@pytest.mark.asyncio
async def test_get_daily_bars_returns_dto_list_with_ohlcv():
    """调用日线查询 Application 接口，断言返回 DTO 列表且每条含 open/high/low/close/vol 等字段。"""
    ticker = "000001.SZ"
    start_date = date(2024, 1, 1)
    end_date = date(2024, 1, 31)

    mock_repo = AsyncMock()
    mock_repo.get_by_third_code_and_date_range.return_value = []

    use_case = GetDailyBarsForTickerUseCase(mock_repo)
    result = await use_case.execute(ticker=ticker, start_date=start_date, end_date=end_date)

    assert isinstance(result, list)
    # 若有数据，每条应为 DailyBarDTO且含开高低收量
    for bar in result:
        assert isinstance(bar, DailyBarDTO)
        assert hasattr(bar, "trade_date")
        assert hasattr(bar, "open")
        assert hasattr(bar, "high")
        assert hasattr(bar, "low")
        assert hasattr(bar, "close")
        assert hasattr(bar, "vol")
