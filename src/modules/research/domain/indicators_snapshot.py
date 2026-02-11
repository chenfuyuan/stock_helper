"""
技术指标与形态的快照结构，供指标计算模块输出、Prompt 填充使用。
以原始数值为主，供大模型自行判断；解读类字段保留作可选辅助。
"""
from typing import List

from pydantic import BaseModel, Field


class TechnicalIndicatorsSnapshot(BaseModel):
    """日线级别计算得到的全部指标原始数值，供技术分析 Prompt 使用。"""

    # 当前价（分析基准日收盘）
    current_price: float = Field(default=0.0, description="当前收盘价")
    # 日涨跌幅（%），来自数据源 pct_chg 或计算
    change_percent: float = Field(default=0.0, description="日涨跌幅（%）")

    # 均线（仅原始数值）
    ma5: float = Field(default=0.0, description="MA5")
    ma10: float = Field(default=0.0, description="MA10")
    ma20: float = Field(default=0.0, description="MA20")
    ma30: float = Field(default=0.0, description="MA30")
    ma60: float = Field(default=0.0, description="MA60")
    ma120: float = Field(default=0.0, description="MA120")
    ma200: float = Field(default=0.0, description="MA200")

    # 动量：RSI
    rsi_value: float = Field(default=0.0, description="RSI(14)")

    # 动量：MACD(12,26,9)
    macd_dif: float = Field(default=0.0, description="MACD DIF")
    macd_dea: float = Field(default=0.0, description="MACD DEA")
    macd_histogram: float = Field(default=0.0, description="MACD 柱状图 DIF-DEA")

    # 动量：KDJ(9,3,3)
    kdj_k: float = Field(default=0.0, description="KDJ K")
    kdj_d: float = Field(default=0.0, description="KDJ D")
    kdj_j: float = Field(default=0.0, description="KDJ J")

    # 趋势：ADX(14)
    adx_value: float = Field(default=0.0, description="ADX(14)")

    # 量能：量比、OBV 趋势
    volume_ratio: float = Field(default=0.0, description="量比（当日量/5日均量）")
    obv_trend: str = Field(default="", description="OBV 5日趋势：Rising / Falling / Flat")

    # 机构成本与布林带、ATR
    vwap_value: float = Field(default=0.0, description="成交量加权均价（周期内 VWAP）")
    price_vs_vwap_status: str = Field(default="", description="当前价相对 VWAP：上方/下方/持平")
    bb_upper: float = Field(default=0.0, description="布林带上轨(20,2)")
    bb_lower: float = Field(default=0.0, description="布林带下轨(20,2)")
    bb_middle: float = Field(default=0.0, description="布林带中轨 MA20")
    bb_bandwidth: float = Field(default=0.0, description="布林带宽(%)")
    atr_value: float = Field(default=0.0, description="ATR(14) 平均真实波幅")

    # 近期高低（供关键价位参考）
    high_20d: float = Field(default=0.0, description="近 20 日最高价")
    low_20d: float = Field(default=0.0, description="近 20 日最低价")

    # 关键价位
    calculated_support_levels: List[float] = Field(default_factory=list, description="支撑位列表")
    calculated_resistance_levels: List[float] = Field(default_factory=list, description="阻力位列表")
    detected_patterns: List[str] = Field(default_factory=list, description="识别到的 K 线形态")
