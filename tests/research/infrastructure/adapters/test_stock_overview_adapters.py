"""
Adapter 空值防护测试（research-input-robustness 1.5）。
覆盖 daily=None、daily 正常、industry=None 三个场景，对 valuation / macro / catalyst 三个适配器。
"""
from datetime import date
from unittest.mock import AsyncMock

import pytest

from src.modules.data_engineering.application.queries.get_stock_basic_info import (
    StockBasicInfoDTO,
)
from src.modules.data_engineering.domain.model.stock import StockInfo
from src.modules.data_engineering.domain.model.stock_daily import StockDaily
from src.modules.research.infrastructure.adapters.valuation_data_adapter import (
    ValuationDataAdapter,
)
from src.modules.research.infrastructure.adapters.macro_data_adapter import (
    MacroDataAdapter,
)
from src.modules.research.infrastructure.adapters.catalyst_data_adapter import (
    CatalystDataAdapter,
)


def _make_info(name: str = "平安银行", industry: str | None = "银行", third_code: str = "000001.SZ") -> StockInfo:
    return StockInfo(
        third_code=third_code,
        symbol="000001",
        name=name,
        industry=industry,
    )


def _make_daily(third_code: str = "000001.SZ") -> StockDaily:
    return StockDaily(
        third_code=third_code,
        trade_date=date(2025, 2, 13),
        open=10.0,
        high=10.5,
        low=9.8,
        close=10.2,
        pre_close=10.0,
        change=0.2,
        pct_chg=2.0,
        vol=1e6,
        amount=1e7,
        pe_ttm=5.0,
        pb=0.6,
        ps_ttm=1.0,
        dv_ratio=3.0,
        total_mv=2000.0,
    )


# ---------- ValuationDataAdapter ----------


@pytest.mark.asyncio
async def test_valuation_adapter_daily_none_returns_none():
    """daily=None 时估值适配器返回 None。"""
    use_case = AsyncMock()
    use_case.execute.return_value = StockBasicInfoDTO(
        info=_make_info(),
        daily=None,
    )
    adapter = ValuationDataAdapter(
        get_stock_basic_info_use_case=use_case,
        get_valuation_dailies_use_case=AsyncMock(),
        get_finance_use_case=AsyncMock(),
    )
    result = await adapter.get_stock_overview("000001.SZ")
    assert result is None


@pytest.mark.asyncio
async def test_valuation_adapter_daily_ok_returns_overview():
    """daily 正常时估值适配器返回 StockOverviewInput。"""
    use_case = AsyncMock()
    use_case.execute.return_value = StockBasicInfoDTO(
        info=_make_info(),
        daily=_make_daily(),
    )
    adapter = ValuationDataAdapter(
        get_stock_basic_info_use_case=use_case,
        get_valuation_dailies_use_case=AsyncMock(),
        get_finance_use_case=AsyncMock(),
    )
    result = await adapter.get_stock_overview("000001.SZ")
    assert result is not None
    assert result.stock_name == "平安银行"
    assert result.industry == "银行"
    assert result.third_code == "000001.SZ"
    assert result.current_price == 10.2


@pytest.mark.asyncio
async def test_valuation_adapter_industry_none_defaults_to_unknown():
    """industry=None 时估值适配器使用默认「未知行业」。"""
    use_case = AsyncMock()
    use_case.execute.return_value = StockBasicInfoDTO(
        info=_make_info(industry=None),
        daily=_make_daily(),
    )
    adapter = ValuationDataAdapter(
        get_stock_basic_info_use_case=use_case,
        get_valuation_dailies_use_case=AsyncMock(),
        get_finance_use_case=AsyncMock(),
    )
    result = await adapter.get_stock_overview("000001.SZ")
    assert result is not None
    assert result.industry == "未知行业"


# ---------- MacroDataAdapter ----------


@pytest.mark.asyncio
async def test_macro_adapter_daily_none_returns_none():
    """daily=None 时宏观适配器返回 None。"""
    use_case = AsyncMock()
    use_case.execute.return_value = StockBasicInfoDTO(
        info=_make_info(),
        daily=None,
    )
    adapter = MacroDataAdapter(
        stock_info_usecase=use_case,
        web_search_service=AsyncMock(),
    )
    result = await adapter.get_stock_overview("000001.SZ")
    assert result is None


@pytest.mark.asyncio
async def test_macro_adapter_daily_ok_returns_overview():
    """daily 正常时宏观适配器返回 MacroStockOverview。"""
    use_case = AsyncMock()
    use_case.execute.return_value = StockBasicInfoDTO(
        info=_make_info(),
        daily=_make_daily(),
    )
    adapter = MacroDataAdapter(
        stock_info_usecase=use_case,
        web_search_service=AsyncMock(),
    )
    result = await adapter.get_stock_overview("000001.SZ")
    assert result is not None
    assert result.stock_name == "平安银行"
    assert result.industry == "银行"
    assert result.third_code == "000001.SZ"


@pytest.mark.asyncio
async def test_macro_adapter_industry_none_defaults_to_unknown():
    """industry=None 时宏观适配器使用默认「未知行业」。"""
    use_case = AsyncMock()
    use_case.execute.return_value = StockBasicInfoDTO(
        info=_make_info(industry=None),
        daily=_make_daily(),
    )
    adapter = MacroDataAdapter(
        stock_info_usecase=use_case,
        web_search_service=AsyncMock(),
    )
    result = await adapter.get_stock_overview("000001.SZ")
    assert result is not None
    assert result.industry == "未知行业"


# ---------- CatalystDataAdapter ----------


@pytest.mark.asyncio
async def test_catalyst_adapter_daily_none_still_returns_overview():
    """催化剂适配器不依赖 daily，daily=None 时仍可从 info 返回概览。"""
    use_case = AsyncMock()
    use_case.execute.return_value = StockBasicInfoDTO(
        info=_make_info(),
        daily=None,
    )
    adapter = CatalystDataAdapter(
        stock_info_use_case=use_case,
        web_search_service=AsyncMock(),
    )
    result = await adapter.get_stock_overview("000001.SZ")
    assert result is not None
    assert result.stock_name == "平安银行"
    assert result.third_code == "000001.SZ"


@pytest.mark.asyncio
async def test_catalyst_adapter_daily_ok_returns_overview():
    """daily 正常时催化剂适配器返回 CatalystStockOverview。"""
    use_case = AsyncMock()
    use_case.execute.return_value = StockBasicInfoDTO(
        info=_make_info(),
        daily=_make_daily(),
    )
    adapter = CatalystDataAdapter(
        stock_info_use_case=use_case,
        web_search_service=AsyncMock(),
    )
    result = await adapter.get_stock_overview("000001.SZ")
    assert result is not None
    assert result.stock_name == "平安银行"
    assert result.industry == "银行"
    assert result.third_code == "000001.SZ"


@pytest.mark.asyncio
async def test_catalyst_adapter_industry_none_defaults_to_unknown():
    """industry=None 时催化剂适配器使用默认「未知行业」。"""
    use_case = AsyncMock()
    use_case.execute.return_value = StockBasicInfoDTO(
        info=_make_info(industry=None),
        daily=None,
    )
    adapter = CatalystDataAdapter(
        stock_info_use_case=use_case,
        web_search_service=AsyncMock(),
    )
    result = await adapter.get_stock_overview("000001.SZ")
    assert result is not None
    assert result.industry == "未知行业"
