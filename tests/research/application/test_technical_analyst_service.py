"""
Task 2.3 Red：技术分析师 Application 接口的测试。
入参至少含 ticker、analysis_date；出参为包含解析结果与 input、technical_indicators、output 的 dict。
编排通过 Port：获取日线 → 指标计算 Port → 技术分析 Agent Port。
"""
import pytest
from datetime import date
from unittest.mock import AsyncMock, MagicMock

from src.modules.research.application.technical_analyst_service import (
    TechnicalAnalystService,
    MIN_BARS_REQUIRED,
)
from src.modules.research.domain.dtos.technical_analysis_dtos import (
    TechnicalAnalysisAgentResult,
    TechnicalAnalysisResultDTO,
    KeyTechnicalLevelsDTO,
)
from src.modules.research.domain.dtos.indicators_snapshot import TechnicalIndicatorsSnapshot
from src.modules.research.domain.dtos.daily_bar_input import DailyBarInput
from src.modules.research.domain.ports.indicator_calculator import IIndicatorCalculator
from src.modules.research.domain.ports.market_quote import IMarketQuotePort
from src.modules.research.domain.ports.technical_analyst_agent import ITechnicalAnalystAgentPort


def _make_result_dto() -> TechnicalAnalysisResultDTO:
    return TechnicalAnalysisResultDTO(
        signal="BULLISH",
        confidence=0.8,
        summary_reasoning="测试",
        key_technical_levels=KeyTechnicalLevelsDTO(support=10.0, resistance=11.0),
        risk_warning="",
    )


def _make_agent_result() -> TechnicalAnalysisAgentResult:
    return TechnicalAnalysisAgentResult(
        result=_make_result_dto(),
        raw_llm_output='{"signal":"BULLISH",...}',
        user_prompt="user prompt content",
    )


def _make_bars():
    """返回不少于 MIN_BARS_REQUIRED 的日线列表，避免触发「K 线数量不足」校验。"""
    from datetime import timedelta
    base = date(2024, 1, 1)
    return [
        DailyBarInput(
            trade_date=base + timedelta(days=i),
            open=10.0,
            high=11.0,
            low=9.0,
            close=10.5 + i * 0.01,
            vol=1e6,
        )
        for i in range(MIN_BARS_REQUIRED)
    ]


@pytest.mark.asyncio
async def test_technical_analyst_accepts_ticker_and_analysis_date_returns_dto():
    """调用技术分析师 Application 接口，出参含解析结果及 input、technical_indicators、output（代码塞入）。"""
    mock_market = AsyncMock(spec=IMarketQuotePort)
    mock_market.get_daily_bars.return_value = _make_bars()

    snapshot = TechnicalIndicatorsSnapshot()
    mock_indicator = MagicMock(spec=IIndicatorCalculator)
    mock_indicator.compute.return_value = snapshot

    mock_agent = AsyncMock(spec=ITechnicalAnalystAgentPort)
    mock_agent.analyze.return_value = _make_agent_result()

    service = TechnicalAnalystService(
        market_quote_port=mock_market,
        indicator_calculator=mock_indicator,
        analyst_agent_port=mock_agent,
    )
    result = await service.run(ticker="000001.SZ", analysis_date=date(2024, 1, 15))

    assert isinstance(result, dict)
    assert result["signal"] in ("BULLISH", "BEARISH", "NEUTRAL")
    assert 0 <= result["confidence"] <= 1
    assert "summary_reasoning" in result and "key_technical_levels" in result and "risk_warning" in result
    assert result["input"] == "user prompt content"
    assert result["output"] == '{"signal":"BULLISH",...}'
    assert "technical_indicators" in result
    assert result["technical_indicators"] == snapshot.model_dump()

    mock_market.get_daily_bars.assert_called_once()
    mock_indicator.compute.assert_called_once_with(_make_bars())
    mock_agent.analyze.assert_called_once()
    call_kw = mock_agent.analyze.call_args[1]
    assert call_kw["ticker"] == "000001.SZ"
    assert call_kw["analysis_date"] == "2024-01-15"
    assert call_kw["snapshot"] == snapshot


@pytest.mark.asyncio
async def test_technical_analyst_raises_when_no_daily_bars():
    """当日线数据为空时拒绝并提示先同步日线（避免指标全空）。"""
    from src.shared.domain.exceptions import BadRequestException

    mock_market = AsyncMock(spec=IMarketQuotePort)
    mock_market.get_daily_bars.return_value = []
    mock_indicator = MagicMock(spec=IIndicatorCalculator)
    mock_agent = AsyncMock(spec=ITechnicalAnalystAgentPort)
    service = TechnicalAnalystService(
        market_quote_port=mock_market,
        indicator_calculator=mock_indicator,
        analyst_agent_port=mock_agent,
    )

    with pytest.raises(BadRequestException) as exc_info:
        await service.run(ticker="002455.SZ", analysis_date=date(2026, 2, 11))

    assert "无日线数据" in exc_info.value.message
    assert "同步" in exc_info.value.message
    mock_agent.analyze.assert_not_called()


@pytest.mark.asyncio
async def test_technical_analyst_rejects_missing_ticker():
    """缺失 ticker 时拒绝并返回可区分错误（Spec：输入缺失关键字段时的行为）。"""
    from src.shared.domain.exceptions import BadRequestException

    mock_market = AsyncMock(spec=IMarketQuotePort)
    mock_indicator = MagicMock(spec=IIndicatorCalculator)
    mock_agent = AsyncMock(spec=ITechnicalAnalystAgentPort)
    service = TechnicalAnalystService(
        market_quote_port=mock_market,
        indicator_calculator=mock_indicator,
        analyst_agent_port=mock_agent,
    )

    with pytest.raises(BadRequestException) as exc_info:
        await service.run(ticker="", analysis_date=date(2024, 1, 15))

    assert "ticker" in exc_info.value.message.lower() or "必填" in exc_info.value.message


@pytest.mark.asyncio
async def test_technical_analyst_raises_when_bars_less_than_min_required():
    """K 线数量 < MIN_BARS_REQUIRED 时抛出 BadRequestException，message 含实际数量与门槛。"""
    from src.shared.domain.exceptions import BadRequestException

    mock_market = AsyncMock(spec=IMarketQuotePort)
    mock_market.get_daily_bars.return_value = _make_bars()[: (MIN_BARS_REQUIRED - 1)]
    mock_indicator = MagicMock(spec=IIndicatorCalculator)
    mock_agent = AsyncMock(spec=ITechnicalAnalystAgentPort)
    service = TechnicalAnalystService(
        market_quote_port=mock_market,
        indicator_calculator=mock_indicator,
        analyst_agent_port=mock_agent,
    )

    with pytest.raises(BadRequestException) as exc_info:
        await service.run(ticker="000001.SZ", analysis_date=date(2024, 1, 15))

    msg = exc_info.value.message
    assert str(MIN_BARS_REQUIRED - 1) in msg or str(MIN_BARS_REQUIRED) in msg
    assert "30" in msg or str(MIN_BARS_REQUIRED) in msg
    mock_agent.analyze.assert_not_called()


@pytest.mark.asyncio
async def test_technical_analyst_rejects_missing_analysis_date():
    """缺失 analysis_date 时拒绝并返回可区分错误。"""
    from src.shared.domain.exceptions import BadRequestException

    mock_market = AsyncMock(spec=IMarketQuotePort)
    mock_indicator = MagicMock(spec=IIndicatorCalculator)
    mock_agent = AsyncMock(spec=ITechnicalAnalystAgentPort)
    service = TechnicalAnalystService(
        market_quote_port=mock_market,
        indicator_calculator=mock_indicator,
        analyst_agent_port=mock_agent,
    )

    with pytest.raises(BadRequestException):
        await service.run(ticker="000001.SZ", analysis_date=None)  # type: ignore
