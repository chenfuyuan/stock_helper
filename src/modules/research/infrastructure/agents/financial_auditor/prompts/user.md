# Target Asset
- Symbol: **{symbol}**
- Report Period: **{report_period}**
- Data Source: **{source}**

# 1. 静态财务快照 (Snapshot - Current Status)
*(评估当前的生存能力与盈利能力)*

## A. 盈利能力 (Profitability)
- **Gross Margin**: {gross_margin}% (毛利率)
- **Net Profit Margin**: {netprofit_margin}% (净利率)
- **ROE (Weighted)**: {roe_waa}% (加权净资产收益率)
- **ROIC**: {roic}% (投入资本回报率 - **Key Metric**)

## B. 每股含金量 (Per Share Quality)
- **EPS (Basic)**: {eps}
- **EPS (Deducted)**: {eps_deducted} (DB: profit_dedt / share 或直接提供总额对比)
- **OCFPS (Operating Cash Flow)**: {ocfps}
- **FCFF PS (Free Cash Flow)**: {fcff_ps} (每股企业自由现金流)
- **Quality Check**: OCFPS / EPS = {quality_ratio} (Target > 1.0)

## C. 资产负债与流动性 (Balance Sheet)
- **Current Ratio**: {current_ratio} (流动比率)
- **Quick Ratio**: {quick_ratio} (速动比率)
- **Debt-to-Assets**: {debt_to_assets}% (资产负债率)
- **Interest Bearing Debt**: {interestdebt} (带息债务)
- **Net Debt**: {netdebt} (净债务)

## D. 运营效率 (Efficiency)
- **Inventory Days**: {invturn_days} (存货周转天数)
- **Receivables Days**: {arturn_days} (应收账款周转天数)
- **Asset Turnover**: {assets_turn} (总资产周转率)

# 2. 历史趋势序列 (Time-Series Analysis)
*(Index 0 = Current, Index 4 = Oldest. Used for Trend & Divergence Detection)*

```json
{{
  "quarters": {quarter_list},                   // ["2024Q1", "2023Q4", ...]
  "revenue_growth_yoy": {revenue_growth_series},// [15.2, 12.0...] -> 营收增速趋势
  "profit_growth_yoy": {profit_growth_series},  // [20.0, 15.0...] -> 利润增速趋势
  "gross_margin_trend": {gross_margin_series},  // [35, 36, 37...] -> 寻找定价权提升
  "roic_trend": {roic_series},                  // [8, 9, 10...] -> 寻找护城河变宽
  "fcff_trend": {fcff_series},                  // [100, -50...] -> 寻找造血能力
  "inventory_days_trend": {invturn_days_series},// [80, 85, 90...] -> 侦测滞销风险
  "receivables_days_trend": {arturn_days_series}// [45, 45, 60...] -> 侦测压货风险
}}
```
