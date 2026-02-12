"""
任务 10.1：估值日线查询 Application 接口的测试。
给定 ticker 与日期区间，调用 data_engineering 的估值日线查询接口，
断言返回 DTO 列表且含 trade_date、close、pe_ttm、pb、ps_ttm、dv_ratio、total_mv 等估值字段。
"""
import pytest
from datetime import date
from unittest.mock import AsyncMock

from src.modules.data_engineering.application.queries.get_valuation_dailies_for_ticker import (
    GetValuationDailiesForTickerUseCase,
    ValuationDailyDTO,
)
from src.modules.data_engineering.domain.model.stock_daily import StockDaily


@pytest.mark.asyncio
async def test_get_valuation_dailies_returns_dto_list_with_valuation_fields():
    """调用估值日线查询 Application 接口，断言返回 DTO 列表且每条含估值字段。"""
    ticker = "000001.SZ"
    start_date = date(2024, 1, 1)
    end_date = date(2024, 1, 31)

    # Mock repository 返回包含估值字段的 StockDaily
    mock_repo = AsyncMock()
    mock_repo.get_valuation_dailies.return_value = [
        StockDaily(
            third_code=ticker,
            trade_date=date(2024, 1, 2),
            open=10.0,
            high=10.5,
            low=9.8,
            close=10.2,
            pre_close=10.0,
            change=0.2,
            pct_chg=2.0,
            vol=1000000.0,
            amount=10000000.0,
            pe_ttm=5.5,
            pb=0.65,
            ps_ttm=1.2,
            dv_ratio=3.5,
            total_mv=200000.0,
        ),
        StockDaily(
            third_code=ticker,
            trade_date=date(2024, 1, 3),
            open=10.2,
            high=10.8,
            low=10.1,
            close=10.6,
            pre_close=10.2,
            change=0.4,
            pct_chg=3.9,
            vol=1200000.0,
            amount=12000000.0,
            pe_ttm=5.7,
            pb=0.68,
            ps_ttm=1.25,
            dv_ratio=3.3,
            total_mv=205000.0,
        ),
    ]

    use_case = GetValuationDailiesForTickerUseCase(mock_repo)
    result = await use_case.execute(
        ticker=ticker, start_date=start_date, end_date=end_date
    )

    assert isinstance(result, list)
    assert len(result) == 2
    
    # 验证 DTO 包含估值字段
    for daily in result:
        assert isinstance(daily, ValuationDailyDTO)
        assert hasattr(daily, "trade_date")
        assert hasattr(daily, "close")
        assert hasattr(daily, "pe_ttm")
        assert hasattr(daily, "pb")
        assert hasattr(daily, "ps_ttm")
        assert hasattr(daily, "dv_ratio")
        assert hasattr(daily, "total_mv")
    
    # 验证具体值
    assert result[0].pe_ttm == 5.5
    assert result[0].pb == 0.65
    assert result[1].pe_ttm == 5.7


@pytest.mark.asyncio
async def test_finance_indicator_dto_contains_bps_field():
    """验证 FinanceIndicatorDTO 包含 bps 字段。"""
    from src.modules.data_engineering.application.queries.get_finance_for_ticker import (
        FinanceIndicatorDTO,
    )
    
    # 验证 DTO 可以接受 bps 字段
    dto = FinanceIndicatorDTO(
        end_date=date(2024, 9, 30),
        ann_date=date(2024, 10, 30),
        third_code="000001.SZ",
        eps=2.0,
        bps=16.0,  # 新增字段
    )
    
    assert dto.bps == 16.0
    assert hasattr(dto, "bps")


@pytest.mark.asyncio
async def test_get_valuation_dailies_calls_correct_repo_method():
    """验证 use case 调用 repository 的 get_valuation_dailies 方法。"""
    ticker = "000001.SZ"
    start_date = date(2024, 1, 1)
    end_date = date(2024, 1, 31)

    mock_repo = AsyncMock()
    mock_repo.get_valuation_dailies.return_value = []

    use_case = GetValuationDailiesForTickerUseCase(mock_repo)
    await use_case.execute(ticker=ticker, start_date=start_date, end_date=end_date)

    # 验证调用了正确的 repository 方法
    mock_repo.get_valuation_dailies.assert_called_once_with(
        third_code=ticker, start_date=start_date, end_date=end_date
    )
