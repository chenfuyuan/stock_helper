# 估值分析任务: {stock_name} ({stock_code})
**当前日期**: {current_date}
**所属行业**: {industry}

---

## 第一部分：市场相对估值 (Market Valuation Snapshots)
*当前价格*: **{current_price} 元**
*总市值*: {total_mv} 亿元

| 核心指标 | 当前数值 | 过去3年历史分位点 (Percentile) | 解读提示 |
| :--- | :--- | :--- | :--- |
| **市盈率 (PE-TTM)** | {pe_ttm} | **{pe_percentile}%** | (越低越便宜; <20% 为低估区) |
| **市净率 (PB)** | {pb} | **{pb_percentile}%** | (越低越便宜; <20% 为低估区) |
| **市销率 (PS)** | {ps_ttm} | {ps_percentile}% | (辅助参考) |
| **股息率 (Dividend)** | {dv_ratio}% | N/A | (越高越好) |

---

## 第二部分：基本面质量体检 (Fundamental Quality)
*用于判断是否存在“价值陷阱”风险*

* **ROE (净资产收益率)**: {roe}%
* **毛利率 (Gross Margin)**: {gros_profit_margin}% (同比趋势: {gross_margin_trend})
* **净利率 (Net Margin)**: {net_profit_margin}%
* **资产负债率 (Debt Ratio)**: {debt_to_assets}%

---

## 第三部分：预计算估值模型 (Pre-calculated Models)
*以下数据由量化引擎生成，请作为核心证据使用*

### 模型 A: PEG 估值 (成长性匹配度)
* **公式**: 市盈率(TTM) / 净利润增长率
* **输入 PE**: {pe_ttm}
* **输入 增长率 (4季平均)**: {growth_rate_avg}%
* **计算结果 (PEG Ratio)**: **{peg_ratio}**
* *判断标准*: < 1.0 (低估/高性价比), 1.0-1.5 (合理), > 2.0 (高估/透支).

### 模型 B: 格雷厄姆数字 (保守内在价值)
* **公式**: Sqrt(22.5 * 每股收益EPS * 每股净资产BPS)
* **计算出的内在价值**: **{graham_intrinsic_val} 元**
* **安全边际 (Safety Margin)**: **{graham_safety_margin}%**
    *(正数代表当前价格低于内在价值，具有安全边际；负数代表溢价)*

---

## 任务指令
请基于上述数据（且仅基于上述数据）生成 JSON 估值报告：
1. **综合判断**：结合历史分位、PEG 和 格雷厄姆模型，判定当前价格状态。
2. **交叉验证**：如果 PE 很低但 ROE 也很低，请警惕“价值陷阱”。
3. **输出**：直接输出 JSON 字符串。