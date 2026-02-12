# 目标资产信息
- 标的代码: {ticker}
- 分析基准日: {analysis_date}

# 硬数据事实 (Hard Data Facts)
以下均为量化引擎计算的**原始数值**。若某指标因数据不足为 null/0，请忽略该条。

## 1. 价格与趋势 (Price & Trend)
- 当前价 (Close): **{current_price}** (日涨跌幅: {change_percent}%)
- 均线系统: MA5=**{ma5}** | MA20=**{ma20}** | MA60=**{ma60}** | MA200=**{ma200}**
- 机构成本 (VWAP): **{vwap_value}** (当前价相对于 VWAP: {price_vs_vwap_status})

## 2. 动量 (Momentum)
- RSI(14): **{rsi_value}**
- MACD(12,26,9): DIF=**{macd_dif}**, DEA=**{macd_dea}**, 柱状图=**{macd_histogram}**
- KDJ(9,3,3): K=**{kdj_k}**, D=**{kdj_d}**

## 3. 波动率与通道 (Volatility & Bands)
- 布林带(20,2): 上轨=**{bb_upper}**, 下轨=**{bb_lower}**, 中轨=**{bb_middle}**
- 布林带宽 (Bandwidth): **{bb_bandwidth}%** (数值越低代表波动率越低，可能变盘)
- ATR(14): **{atr_value}** (平均真实波幅)

## 4. 量能与资金 (Volume & Flow)
- 量比 (Vol/MA5_Vol): **{volume_ratio}**
- OBV 趋势 (5日): **{obv_trend}** (例如: Rising, Falling, Flat)

## 5. 关键价位 (Levels)
- 自动计算支撑位 (由近及远): {calculated_support_levels}
- 自动计算阻力位 (由近及远): {calculated_resistance_levels}
- 识别形态: {detected_patterns} (例如: Bull Flag, Head and Shoulders, None)

# 分析逻辑与任务
请基于上述数据，按照 CMT 标准流程进行推理：

1.  **趋势识别**：基于 MA 排列与 VWAP 位置判断主趋势（多头/空头/震荡）。
2.  **位置评估**：利用布林带与乖离率判断当前价格是否过热（Overextended）或处于压缩爆发期（Squeeze）。
3.  **动量确认**：检查 RSI 与 MACD 是否支持当前价格方向，寻找**背离**信号。
4.  **价位筛选**：从提供的支撑/阻力列表中，选取**共振最强**（如均线与计算位重合）或**最具备操作意义**的一个价位填入 JSON。

**输出 JSON 结构定义**：
- **signal**: 字符串，仅限 `BULLISH` / `BEARISH` / `NEUTRAL`。
- **confidence**: 数字，0.0 ~ 1.0。若指标冲突（如趋势向上但顶背离）请降低置信度。
- **summary_reasoning**: 字符串。综合分析摘要，必须引用具体数值（如 "RSI 达 75"、"价格站稳 VWAP"）。
- **key_technical_levels**: 对象，包含 `support` (float) 和 `resistance` (float)。必须是单一数值。
- **risk_warning**: 字符串。说明观点失效的条件（如："若跌破布林中轨 {bb_middle} 则看多观点失效"）。

**JSON 输出示例**（仅供参考结构，请填入实际分析结果）：
{{"signal": "NEUTRAL", "confidence": 0.6, "summary_reasoning": "价格位于 MA20 (105.2) 之上但受阻于布林上轨...", "key_technical_levels": {{"support": 100.0, "resistance": 110.0}}, "risk_warning": "..."}}
