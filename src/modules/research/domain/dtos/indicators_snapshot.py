"""
技术指标与形态的快照结构，供指标计算模块输出、Prompt 填充使用。
以原始数值为主，供大模型自行判断；解读类字段保留作可选辅助。
数据不足无法计算的指标为 None，填充 Prompt 时转为 "N/A"。
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class TechnicalIndicatorsSnapshot(BaseModel):
    """日线级别计算得到的全部指标原始数值，供技术分析 Prompt 使用。"""

    current_price: float = Field(default=0.0, description="当前收盘价")
    change_percent: float = Field(default=0.0, description="日涨跌幅（%）")

    ma5: float = Field(default=0.0, description="MA5")
    ma10: float = Field(default=0.0, description="MA10")
    ma20: float = Field(default=0.0, description="MA20")
    ma30: float = Field(default=0.0, description="MA30")
    ma60: float = Field(default=0.0, description="MA60")
    ma120: float = Field(default=0.0, description="MA120")
    ma200: float = Field(default=0.0, description="MA200")

    rsi_value: Optional[float] = Field(default=None, description="RSI(14)，数据不足时为 None")
    macd_dif: Optional[float] = Field(default=None, description="MACD DIF")
    macd_dea: Optional[float] = Field(default=None, description="MACD DEA")
    macd_histogram: Optional[float] = Field(default=None, description="MACD 柱状图 DIF-DEA")
    kdj_k: Optional[float] = Field(default=None, description="KDJ K")
    kdj_d: Optional[float] = Field(default=None, description="KDJ D")
    kdj_j: Optional[float] = Field(default=None, description="KDJ J")
    adx_value: Optional[float] = Field(default=None, description="ADX(14)")
    volume_ratio: Optional[float] = Field(default=None, description="量比（当日量/5日均量）")
    obv_trend: str = Field(default="", description="OBV 5日趋势：Rising / Falling / Flat")
    vwap_value: Optional[float] = Field(default=None, description="成交量加权均价（周期内 VWAP）")
    price_vs_vwap_status: str = Field(default="", description="当前价相对 VWAP：上方/下方/持平")
    bb_upper: Optional[float] = Field(default=None, description="布林带上轨(20,2)")
    bb_lower: Optional[float] = Field(default=None, description="布林带下轨(20,2)")
    bb_middle: Optional[float] = Field(default=None, description="布林带中轨 MA20")
    bb_bandwidth: Optional[float] = Field(default=None, description="布林带宽(%)")
    atr_value: Optional[float] = Field(default=None, description="ATR(14) 平均真实波幅")
    high_20d: float = Field(default=0.0, description="近 20 日最高价")
    low_20d: float = Field(default=0.0, description="近 20 日最低价")
    calculated_support_levels: List[float] = Field(default_factory=list, description="支撑位列表")
    calculated_resistance_levels: List[float] = Field(
        default_factory=list, description="阻力位列表"
    )
    detected_patterns: List[str] = Field(default_factory=list, description="识别到的 K 线形态")
