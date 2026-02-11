# 目标资产信息
- 标的代码: {ticker}
- 分析基准日: {analysis_date}
- 当前价格: {current_price}

# 硬数据事实 (Hard Data Facts)
以下指标已由量化引擎计算完毕，请基于此进行分析：

## 1. 趋势与均线系统 (Trend)
- 均线状态: 价格位于 MA20 {ma20_position} (上方/下方), 位于 MA200 {ma200_position} (上方/下方)
- 均线排列: {ma_alignment}
- 趋势强度 (ADX): {adx_value} ({adx_interpretation})

## 2. 动量与震荡指标 (Momentum)
- RSI (14): {rsi_value} ({rsi_status})
- MACD: {macd_status}
- KDJ / Stochastic: {kdj_status}

## 3. 量能分析 (Volume)
- 成交量状态: {volume_status}
- 资金流向 (OBV): {obv_trend}

## 4. 形态识别 (Pattern Recognition)
- 识别到的 K 线形态: {detected_patterns}
- 计算支撑位 (Support): {calculated_support_levels}
- 计算阻力位 (Resistance): {calculated_resistance_levels}

# 分析任务
请基于上述数据，生成一份技术分析简报。请以 JSON 格式返回，仅输出一个合法 JSON 对象（不要 Markdown 代码块）。

**必填字段与类型**（严格遵循，否则解析失败）：
- signal：字符串，仅限 BULLISH / BEARISH / NEUTRAL
- confidence：数字，0 到 1 之间
- summary_reasoning：字符串
- key_technical_levels：对象，且 **support 与 resistance 各为一个数字（float）**，表示一个关键支撑位和一个关键阻力位；若无明确价位可填 0.0，**不要使用数组**
- risk_warning：字符串
