"""
Task 1.4：财务数据查询 Application 接口的测试。
给定 ticker 与 limit，调用 data_engineering 的财务查询接口，断言返回 DTO 列表且含盈利/效率/偿债/现金流等字段。
"""

from datetime import date
from unittest.mock import AsyncMock

import pytest

from src.modules.data_engineering.application.queries.get_finance_for_ticker import (
    FinanceIndicatorDTO,
    GetFinanceForTickerUseCase,
)
from src.modules.data_engineering.domain.model.financial_report import (
    StockFinance,
)


def _make_stock_finance() -> StockFinance:
    """构造一条测试用财务记录。"""
    return StockFinance(
        third_code="000001.SZ",
        ann_date=date(2024, 10, 30),
        end_date=date(2024, 9, 30),
        gross_margin=35.5,
        netprofit_margin=12.0,
        roe_waa=15.2,
        roic=10.5,
        eps=1.2,
        profit_dedt=1.0,
        ocfps=1.5,
        fcff_ps=0.8,
        current_ratio=1.8,
        quick_ratio=1.2,
        debt_to_assets=45.0,
        interestdebt=1000000.0,
        netdebt=500000.0,
        invturn_days=60.0,
        arturn_days=45.0,
        assets_turn=0.8,
        total_revenue_ps=10.0,
        fcff=5000000.0,
    )


@pytest.mark.asyncio
async def test_get_finance_returns_dto_list_with_financial_fields():
    """调用财务查询 Application 接口，断言返回 DTO 列表且每条含盈利/效率/偿债/现金流等字段。"""
    ticker = "000001.SZ"
    limit = 5

    mock_repo = AsyncMock()
    mock_repo.get_by_third_code_recent.return_value = [_make_stock_finance()]

    use_case = GetFinanceForTickerUseCase(mock_repo)
    result = await use_case.execute(ticker=ticker, limit=limit)

    assert isinstance(result, list)
    assert len(result) == 1
    dto = result[0]
    assert isinstance(dto, FinanceIndicatorDTO)
    assert dto.third_code == ticker
    assert dto.end_date == date(2024, 9, 30)
    # 盈利
    assert hasattr(dto, "gross_margin")
    assert hasattr(dto, "netprofit_margin")
    assert hasattr(dto, "roe_waa")
    assert hasattr(dto, "roic")
    # 每股含金量
    assert hasattr(dto, "eps")
    assert hasattr(dto, "ocfps")
    assert hasattr(dto, "fcff_ps")
    # 偿债
    assert hasattr(dto, "current_ratio")
    assert hasattr(dto, "quick_ratio")
    assert hasattr(dto, "debt_to_assets")
    # 效率
    assert hasattr(dto, "invturn_days")
    assert hasattr(dto, "arturn_days")
    assert hasattr(dto, "assets_turn")
    assert dto.gross_margin == 35.5
    assert dto.roic == 10.5


@pytest.mark.asyncio
async def test_get_finance_returns_empty_list_when_no_data():
    """当标的无财务数据时，返回空列表。"""
    mock_repo = AsyncMock()
    mock_repo.get_by_third_code_recent.return_value = []

    use_case = GetFinanceForTickerUseCase(mock_repo)
    result = await use_case.execute(ticker="999999.SZ", limit=5)

    assert result == []
