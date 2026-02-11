"""
技术指标与形态的快照结构，与 Spec 输入契约一致。
供指标计算模块输出、Prompt 填充使用。
"""
from typing import List, Optional
from pydantic import BaseModel, Field


class TechnicalIndicatorsSnapshot(BaseModel):
    """与 spec 输入契约一致：趋势/均线、动量、量能、形态与关键价位。"""

    # 趋势与均线
    ma20_position: str = Field(default="", description="价格相对 MA20：上方/下方")
    ma200_position: str = Field(default="", description="价格相对 MA200：上方/下方")
    ma_alignment: str = Field(default="", description="均线排列：多头排列/空头排列/纠缠震荡")
    adx_value: float = Field(default=0.0, description="ADX 值")
    adx_interpretation: str = Field(default="", description="ADX 解读")

    # 动量
    rsi_value: float = Field(default=0.0, description="RSI(14)")
    rsi_status: str = Field(default="", description="超买/中性/超卖")
    macd_status: str = Field(default="", description="MACD 状态描述")
    kdj_status: str = Field(default="", description="KDJ 状态描述")

    # 量能
    volume_status: str = Field(default="", description="成交量状态")
    obv_trend: str = Field(default="", description="OBV 趋势")

    # 形态与关键价位
    detected_patterns: List[str] = Field(default_factory=list, description="识别到的 K 线形态")
    calculated_support_levels: List[float] = Field(default_factory=list, description="支撑位列表")
    calculated_resistance_levels: List[float] = Field(default_factory=list, description="阻力位列表")

    # 当前价（分析基准日）
    current_price: float = Field(default=0.0, description="当前价格")
