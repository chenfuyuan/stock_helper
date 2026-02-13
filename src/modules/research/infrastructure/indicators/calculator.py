"""
基于日线计算技术指标，输出全量原始数值供 Prompt 使用。
实现：多周期 MA、RSI、MACD、KDJ、ADX、量比、支撑/阻力。
数据不足时对应指标返回 None，由调用方填入 N/A。
"""
from typing import List, Optional, Tuple

from src.modules.research.domain.dtos.daily_bar_input import DailyBarInput
from src.modules.research.domain.dtos.indicators_snapshot import TechnicalIndicatorsSnapshot


def _sma(values: List[float], period: int) -> float:
    """周期 period 的简单移动平均，取序列末尾。"""
    if not values or len(values) < period:
        return 0.0
    return sum(values[-period:]) / period


def _ema(values: List[float], period: int) -> float:
    """周期 period 的指数移动平均，取序列末尾。首值为前 period 日 SMA，随后 EMA。"""
    if not values or len(values) < period:
        return 0.0
    alpha = 2.0 / (period + 1)
    ema = sum(values[:period]) / period
    for i in range(period, len(values)):
        ema = alpha * values[i] + (1 - alpha) * ema
    return ema


def _rsi(closes: List[float], period: int = 14) -> Optional[float]:
    """RSI(period)，取序列末尾。数据不足时返回 None。"""
    if len(closes) < period + 1:
        return None
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


def _macd(closes: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    """MACD：返回 (DIF, DEA, 柱状图)。DEA 为 DIF 的 signal 日 EMA。数据不足时返回 (None, None, None)。"""
    if len(closes) < slow:
        return None, None, None
    # 逐日 EMA 得到 DIF 序列（从第 slow 日起）
    difs: List[float] = []
    for n in range(slow - 1, len(closes)):
        sub = closes[: n + 1]
        e1 = _ema(sub, fast)
        e2 = _ema(sub, slow)
        difs.append(e1 - e2)
    if not difs:
        return None, None, None
    dif = difs[-1]
    if len(difs) < signal:
        return round(dif, 4), round(dif, 4), None
    dea = _ema(difs, signal)
    hist = dif - dea
    return round(dif, 4), round(dea, 4), round(hist, 4)


def _kdj(highs: List[float], lows: List[float], closes: List[float], n: int = 9, m1: int = 3, m2: int = 3) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    """KDJ(n,m1,m2)：取最后一日的 K, D, J。数据不足时返回 (None, None, None)。"""
    if len(closes) < n:
        return None, None, None
    k_prev, d_prev = 50.0, 50.0
    for i in range(n - 1, len(closes)):
        high_n = max(highs[i - n + 1 : i + 1])
        low_n = min(lows[i - n + 1 : i + 1])
        if high_n <= low_n:
            rsv = 50.0
        else:
            rsv = (closes[i] - low_n) / (high_n - low_n) * 100.0
        k_prev = (m1 - 1) / m1 * k_prev + 1 / m1 * rsv
        d_prev = (m2 - 1) / m2 * d_prev + 1 / m2 * k_prev
    j = 3 * k_prev - 2 * d_prev
    return round(k_prev, 2), round(d_prev, 2), round(j, 2)


def _vwap(bars: List[DailyBarInput], lookback: int = 0) -> Optional[float]:
    """周期内成交量加权均价：典型价 (H+L+C)/3 * vol 的加权。lookback=0 表示全部。无数据或无成交量时返回 None。"""
    if not bars:
        return None
    start = -lookback if lookback and len(bars) >= lookback else 0
    subset = bars[start:]
    total_pv = sum((b.high + b.low + b.close) / 3.0 * b.vol for b in subset)
    total_v = sum(b.vol for b in subset)
    return round(total_pv / total_v, 4) if total_v > 0 else None


def _bollinger(closes: List[float], period: int = 20, k: float = 2.0) -> Tuple[Optional[float], Optional[float], Optional[float], Optional[float]]:
    """布林带(20,2)：返回 (upper, lower, middle, bandwidth%)。数据不足时返回 (None, None, None, None)。"""
    if len(closes) < period:
        return None, None, None, None
    slice_c = closes[-period:]
    middle = sum(slice_c) / period
    variance = sum((x - middle) ** 2 for x in slice_c) / period
    std = (variance ** 0.5) if variance > 0 else 0.0
    upper = middle + k * std
    lower = middle - k * std
    bandwidth = (upper - lower) / middle * 100.0 if middle and middle != 0 else 0.0
    return round(upper, 4), round(lower, 4), round(middle, 4), round(bandwidth, 2)


def _atr(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> Optional[float]:
    """ATR(period)：Wilder 平滑的真实波幅。数据不足时返回 None。"""
    if len(closes) < period + 1:
        return None
    tr_list: List[float] = []
    for i in range(1, len(closes)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        tr_list.append(tr)
    if len(tr_list) < period:
        return None
    atr = sum(tr_list[:period]) / period
    for i in range(period, len(tr_list)):
        atr = (atr * (period - 1) + tr_list[i]) / period
    return round(atr, 4)


def _obv_trend(closes: List[float], vols: List[float], days: int = 5) -> str:
    """OBV 累计后，比较当前与 days 日前，返回 Rising / Falling / Flat。"""
    if len(closes) < 2 or len(vols) < 2 or len(closes) != len(vols) or days < 1:
        return "Flat"
    obv_list: List[float] = [0.0]
    for i in range(1, len(closes)):
        if closes[i] > closes[i - 1]:
            obv_list.append(obv_list[-1] + vols[i])
        elif closes[i] < closes[i - 1]:
            obv_list.append(obv_list[-1] - vols[i])
        else:
            obv_list.append(obv_list[-1])
    if len(obv_list) <= days:
        return "Flat"
    now_obv = obv_list[-1]
    past_obv = obv_list[-1 - days]
    if now_obv > past_obv:
        return "Rising"
    if now_obv < past_obv:
        return "Falling"
    return "Flat"


def _adx(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> Optional[float]:
    """ADX(period)，Wilder 平滑。返回序列末尾的 ADX。数据不足时返回 None。"""
    if len(closes) < period + 1:
        return None
    tr_list: List[float] = []
    plus_dm: List[float] = []
    minus_dm: List[float] = []
    for i in range(1, len(closes)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        tr_list.append(tr)
        up = highs[i] - highs[i - 1]
        down = lows[i - 1] - lows[i]
        plus_dm.append(up if up > down and up > 0 else 0.0)
        minus_dm.append(down if down > up and down > 0 else 0.0)
    if len(tr_list) < period:
        return None
    # Wilder 平滑：首日为 period 日之和，之后 smooth = prev * (period-1)/period + new
    def wilder_smooth(arr: List[float], p: int) -> List[float]:
        out: List[float] = []
        s = sum(arr[:p])
        out.append(s)
        for i in range(p, len(arr)):
            s = s * (p - 1) / p + arr[i]
            out.append(s)
        return out

    tr_s = wilder_smooth(tr_list, period)
    plus_s = wilder_smooth(plus_dm, period)
    minus_s = wilder_smooth(minus_dm, period)
    di_plus: List[float] = []
    di_minus: List[float] = []
    for i in range(len(tr_s)):
        if tr_s[i] <= 0:
            di_plus.append(0.0)
            di_minus.append(0.0)
        else:
            di_plus.append(100.0 * plus_s[i] / tr_s[i])
            di_minus.append(100.0 * minus_s[i] / tr_s[i])
    dx_list: List[float] = []
    for i in range(len(di_plus)):
        s = di_plus[i] + di_minus[i]
        if s <= 0:
            dx_list.append(0.0)
        else:
            dx_list.append(100.0 * abs(di_plus[i] - di_minus[i]) / s)
    if len(dx_list) < period:
        return None
    adx_smooth = sum(dx_list[:period]) / period
    for i in range(period, len(dx_list)):
        adx_smooth = (adx_smooth * (period - 1) + dx_list[i]) / period
    return round(adx_smooth, 2)


def compute_technical_indicators(bars: List[DailyBarInput]) -> TechnicalIndicatorsSnapshot:
    """
    基于日线序列计算全量技术指标，仅输出原始数值，供 Prompt 与大模型判断。
    """
    if not bars:
        return TechnicalIndicatorsSnapshot()

    closes = [b.close for b in bars]
    highs = [b.high for b in bars]
    lows = [b.low for b in bars]
    vols = [b.vol for b in bars]
    current = closes[-1] if closes else 0.0
    change_percent = bars[-1].pct_chg if bars else 0.0

    def ma_or_fallback(period: int) -> float:
        if len(closes) >= period:
            return round(_sma(closes, period), 4)
        return round(_sma(closes, len(closes)), 4) if closes else 0.0

    ma5 = ma_or_fallback(5)
    ma10 = ma_or_fallback(10)
    ma20 = ma_or_fallback(20)
    ma30 = ma_or_fallback(30)
    ma60 = ma_or_fallback(60)
    ma120 = ma_or_fallback(120) if len(closes) >= 120 else ma60
    ma200 = ma_or_fallback(200) if len(closes) >= 200 else ma120

    rsi_val = _rsi(closes, 14)
    macd_dif, macd_dea, macd_hist = _macd(closes, 12, 26, 9)
    kdj_k, kdj_d, kdj_j = _kdj(highs, lows, closes, 9, 3, 3)
    adx_val = _adx(highs, lows, closes, 14)

    # 量比：当日量 / 5 日均量，数据不足时为 None
    if vols and len(vols) >= 5:
        vol_ma5 = _sma(vols, 5)
        volume_ratio = round((vols[-1] / vol_ma5), 4) if vol_ma5 > 0 else None
    else:
        volume_ratio = None

    # 近 20 日最高/最低
    lookback = min(20, len(highs))
    high_20d = max(highs[-lookback:]) if highs else 0.0
    low_20d = min(lows[-lookback:]) if lows else 0.0

    # 支撑/阻力：近期高低
    support_levels = sorted(set(lows[-lookback:]))[:3]
    resistance_levels = sorted(set(highs[-lookback:]), reverse=True)[:3]

    # VWAP（取近 20 日或全部）、当前价相对 VWAP
    vwap_val = _vwap(bars, 20) if len(bars) >= 20 else _vwap(bars, 0)
    if vwap_val is not None and vwap_val != 0:
        if current > vwap_val:
            price_vs_vwap_status = "上方"
        elif current < vwap_val:
            price_vs_vwap_status = "下方"
        else:
            price_vs_vwap_status = "持平"
    else:
        price_vs_vwap_status = ""

    # 布林带(20,2)、ATR(14)、OBV 5日趋势
    bb_upper, bb_lower, bb_middle, bb_bandwidth = _bollinger(closes, 20, 2.0)
    atr_val = _atr(highs, lows, closes, 14)
    obv_trend_str = _obv_trend(closes, vols, 5)

    return TechnicalIndicatorsSnapshot(
        current_price=round(current, 4),
        change_percent=round(change_percent, 2),
        ma5=ma5,
        ma10=ma10,
        ma20=ma20,
        ma30=ma30,
        ma60=ma60,
        ma120=ma120,
        ma200=ma200,
        rsi_value=round(rsi_val, 2) if rsi_val is not None else None,
        macd_dif=macd_dif,
        macd_dea=macd_dea,
        macd_histogram=macd_hist,
        kdj_k=kdj_k,
        kdj_d=kdj_d,
        kdj_j=kdj_j,
        adx_value=adx_val,
        volume_ratio=volume_ratio,
        obv_trend=obv_trend_str,
        vwap_value=vwap_val,
        price_vs_vwap_status=price_vs_vwap_status,
        bb_upper=bb_upper,
        bb_lower=bb_lower,
        bb_middle=bb_middle,
        bb_bandwidth=bb_bandwidth,
        atr_value=atr_val,
        high_20d=round(high_20d, 4),
        low_20d=round(low_20d, 4),
        calculated_support_levels=support_levels,
        calculated_resistance_levels=resistance_levels,
        detected_patterns=[],
    )
