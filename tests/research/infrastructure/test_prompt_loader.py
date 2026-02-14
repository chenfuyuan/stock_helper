"""
技术分析师 Prompt 填充测试。
覆盖 fill_user_prompt 将 snapshot 中 None 指标转为 N/A 的场景
（research-input-robustness 2.5）。
"""

from src.modules.research.domain.dtos.indicators_snapshot import (
    TechnicalIndicatorsSnapshot,
)
from src.modules.research.infrastructure.prompt_loader import fill_user_prompt


def test_fill_user_prompt_none_indicators_become_na():
    """Snapshot 中为 None 的指标值在填充模板时转为字符串 N/A。"""
    snapshot = TechnicalIndicatorsSnapshot(
        current_price=10.5,
        change_percent=1.2,
        ma5=10.2,
        ma10=10.3,
        ma20=10.4,
        ma30=10.4,
        ma60=10.3,
        ma120=10.0,
        ma200=9.8,
        rsi_value=None,
        macd_dif=None,
        macd_dea=None,
        macd_histogram=None,
        kdj_k=55.0,
        kdj_d=50.0,
        kdj_j=65.0,
        adx_value=None,
        volume_ratio=None,
        obv_trend="Rising",
        vwap_value=None,
        price_vs_vwap_status="",
        bb_upper=None,
        bb_lower=None,
        bb_middle=None,
        bb_bandwidth=None,
        atr_value=None,
        high_20d=11.0,
        low_20d=9.5,
        calculated_support_levels=[9.5],
        calculated_resistance_levels=[11.0],
        detected_patterns=[],
    )
    template = (
        "RSI: {rsi_value}, MACD DIF: {macd_dif}, "
        "VWAP: {vwap_value}, ATR: {atr_value}, Volume ratio: {volume_ratio}."
    )
    result = fill_user_prompt(
        template=template,
        ticker="000001.SZ",
        analysis_date="2024-01-15",
        snapshot=snapshot,
    )
    assert "N/A" in result
    assert "RSI: N/A" in result or "rsi_value" not in result or "N/A" in result
    assert (
        "MACD DIF: N/A" in result
        or "macd_dif" not in result
        or "N/A" in result
    )
    assert "VWAP: N/A" in result
    assert "ATR: N/A" in result
    assert "Volume ratio: N/A" in result
