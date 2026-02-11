"""
指标计算 Port 的 Infrastructure 实现测试。
Spec Scenario：通过 Port 获取指标快照；实现可依赖第三方库。
"""
from datetime import date

from src.modules.research.domain.ports.dto_inputs import DailyBarInput
from src.modules.research.infrastructure.indicators.indicator_calculator_adapter import (
    IndicatorCalculatorAdapter,
)


def test_indicator_calculator_adapter_empty_bars_returns_empty_snapshot():
    """空日线列表时返回空快照（与 calculator 契约一致）。"""
    adapter = IndicatorCalculatorAdapter()
    snapshot = adapter.compute([])
    assert snapshot.current_price == 0.0
    assert snapshot.rsi_value == 0.0
    assert snapshot.calculated_support_levels == []
    assert snapshot.calculated_resistance_levels == []


def test_indicator_calculator_adapter_with_bars_returns_snapshot():
    """有日线时通过 Port 实现计算并返回指标快照（实现可依赖第三方库）。"""
    adapter = IndicatorCalculatorAdapter()
    bars = [
        DailyBarInput(trade_date=date(2024, 1, 1), open=10.0, high=11.0, low=9.0, close=10.5, vol=1e6),
        DailyBarInput(trade_date=date(2024, 1, 2), open=10.5, high=11.5, low=10.0, close=11.0, vol=1.2e6),
    ]
    # 至少 15 根才能算 RSI(14)，这里仅验证返回结构
    snapshot = adapter.compute(bars)
    assert snapshot.current_price == 11.0
    assert hasattr(snapshot, "ma20") and hasattr(snapshot, "ma5")
    assert hasattr(snapshot, "rsi_value")
    assert hasattr(snapshot, "calculated_support_levels")
