"""
基于日线计算技术指标与简单支撑/阻力，输出与 spec 输入契约一致的结构。
本迭代实现 RSI、简单 MA、近期高低作为支撑/阻力；ADX/MACD/KDJ/OBV 为占位，后续可扩展。
"""
from typing import List

from src.modules.research.domain.ports.dto_inputs import DailyBarInput
from src.modules.research.domain.indicators_snapshot import TechnicalIndicatorsSnapshot


def _sma(values: List[float], period: int) -> float:
    if not values or len(values) < period:
        return 0.0
    return sum(values[-period:]) / period


def _rsi(closes: List[float], period: int = 14) -> float:
    if len(closes) < period + 1:
        return 50.0
    gains, losses = [], []
    for i in range(len(closes) - period, len(closes)):
        delta = closes[i] - closes[i - 1]
        gains.append(max(delta, 0.0))
        losses.append(max(-delta, 0.0))
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1 + rs))


def compute_technical_indicators(bars: List[DailyBarInput]) -> TechnicalIndicatorsSnapshot:
    """
    基于日线序列计算技术指标与简单支撑/阻力，返回与 spec 输入契约一致的结构。
    """
    if not bars:
        return TechnicalIndicatorsSnapshot()

    closes = [b.close for b in bars]
    highs = [b.high for b in bars]
    lows = [b.low for b in bars]
    current = closes[-1] if closes else 0.0

    ma20 = _sma(closes, 20) if len(closes) >= 20 else (sum(closes) / len(closes) if closes else 0.0)
    ma200 = _sma(closes, 200) if len(closes) >= 200 else ma20
    ma20_position = "上方" if current >= ma20 else "下方"
    ma200_position = "上方" if current >= ma200 else "下方"
    ma_alignment = "多头排列" if ma20 >= ma200 else "空头排列" if ma20 < ma200 else "纠缠震荡"

    rsi_val = _rsi(closes, 14)
    if rsi_val >= 70:
        rsi_status = "超买"
    elif rsi_val <= 30:
        rsi_status = "超卖"
    else:
        rsi_status = "中性"

    # 简单支撑/阻力：近期 N 根 K 线最低/最高
    lookback = min(20, len(lows))
    support_levels = sorted(set(lows[-lookback:]))[:3]
    resistance_levels = sorted(set(highs[-lookback:]), reverse=True)[:3]

    return TechnicalIndicatorsSnapshot(
        ma20_position=ma20_position,
        ma200_position=ma200_position,
        ma_alignment=ma_alignment,
        adx_value=0.0,
        adx_interpretation="（占位，待实现）",
        rsi_value=round(rsi_val, 2),
        rsi_status=rsi_status,
        macd_status="（占位，待实现）",
        kdj_status="（占位，待实现）",
        volume_status="（占位，待实现）",
        obv_trend="（占位，待实现）",
        detected_patterns=[],
        calculated_support_levels=support_levels,
        calculated_resistance_levels=resistance_levels,
        current_price=current,
    )
