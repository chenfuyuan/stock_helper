# Spec: financial-data-sanity

在估值快照构建阶段增加财务指标合理性校验，拦截上游数据异常（如毛利率 4500 万%），防止 LLM 在异常输入上产生不可靠的分析结论。涉及 ValuationSnapshotBuilderImpl 及毛利率趋势计算。

**测试约定**：每个 `#### Scenario:` 在变更**交付时**须对应至少一个自动化测试用例（单元或集成）；实现顺序可先实现再补测，以完整测试通过为需求完成标准。

---

## Requirements

### Requirement: 关键财务指标合理性边界校验
`ValuationSnapshotBuilderImpl.build()` 在将上游财务数据填入 `ValuationSnapshotDTO` 前，SHALL 对以下关键财务指标进行合理性边界校验。超出合理范围的值 SHALL 被替换为 `"N/A"`（与 `PlaceholderValue` 类型兼容），并记录 WARNING 级别日志（包含字段名、原始值、标的信息）。

校验范围（业务合理性阈值）：
- **毛利率 (gross_margin)**：有效范围 [-100, 100]。毛利率定义为 (营收-成本)/营收，理论上不可能超出 ±100%。
- **ROE (roe_waa)**：有效范围 [-500, 500]。极端亏损或极低净资产时可能出现较大绝对值，但超过 ±500% 几乎不可能是真实数据。
- **净利率 (netprofit_margin)**：有效范围 [-1000, 1000]。允许较宽范围以容纳微利/微营收公司。
- **资产负债率 (debt_to_assets)**：有效范围 [0, 300]。负债可以超过资产（资不抵债），但 300% 以上几乎不可能。

#### Scenario: 毛利率异常（真实案例：44,969,179.57%）
- **WHEN** `ValuationSnapshotBuilderImpl.build()` 被调用，且 `latest_finance.gross_margin` 的值为 `44969179.57`（超出 [-100, 100] 范围）
- **THEN** `ValuationSnapshotDTO.gros_profit_margin` SHALL 为 `"N/A"`，且记录 WARNING 日志说明毛利率值异常

#### Scenario: ROE 异常
- **WHEN** `ValuationSnapshotBuilderImpl.build()` 被调用，且 `latest_finance.roe_waa` 的值超出 [-500, 500] 范围
- **THEN** `ValuationSnapshotDTO.roe` SHALL 为 `"N/A"`，且记录 WARNING 日志说明 ROE 值异常

#### Scenario: 净利率异常
- **WHEN** `ValuationSnapshotBuilderImpl.build()` 被调用，且 `latest_finance.netprofit_margin` 的值超出 [-1000, 1000] 范围
- **THEN** `ValuationSnapshotDTO.net_profit_margin` SHALL 为 `"N/A"`，且记录 WARNING 日志

#### Scenario: 资产负债率异常
- **WHEN** `ValuationSnapshotBuilderImpl.build()` 被调用，且 `latest_finance.debt_to_assets` 的值超出 [0, 300] 范围
- **THEN** `ValuationSnapshotDTO.debt_to_assets` SHALL 为 `"N/A"`，且记录 WARNING 日志

#### Scenario: 所有指标在合理范围内
- **WHEN** `ValuationSnapshotBuilderImpl.build()` 被调用，且所有财务指标均在合理范围内
- **THEN** 行为与当前一致，正常填入数值，无额外 WARNING 日志

---

### Requirement: 毛利率趋势计算防御异常基础值
`_calculate_gross_margin_trend()` 在比较两期毛利率时，SHALL 先校验两期基础值是否均在合理范围内（[-100, 100]）。若任一基础值超出范围，趋势计算 SHALL 返回 `"N/A"` 而非产生荒谬的趋势描述（如"同比上升 5,502,560.9%"）。

#### Scenario: 基础值异常导致趋势无效
- **WHEN** `_calculate_gross_margin_trend()` 被调用，且最新期 `gross_margin` 为 `44969179.57`（超出合理范围）
- **THEN** 函数 SHALL 返回 `"N/A"`，不输出误导性的趋势描述

#### Scenario: 两期均在合理范围内
- **WHEN** `_calculate_gross_margin_trend()` 被调用，且最新期和上一期 `gross_margin` 均在 [-100, 100] 范围内
- **THEN** 行为与当前一致，正常计算同比趋势

#### Scenario: 仅一期异常
- **WHEN** `_calculate_gross_margin_trend()` 被调用，最新期 `gross_margin` 在合理范围内，但上一期超出范围（或反之）
- **THEN** 函数 SHALL 返回 `"N/A"`

---

### Requirement: 合理性阈值集中定义
所有财务指标的合理性阈值 SHALL 以模块级常量形式集中定义在 `ValuationSnapshotBuilderImpl` 所在模块中（`infrastructure/valuation_snapshot/snapshot_builder.py`），便于后续根据业务需求调整。不使用魔数。

#### Scenario: 阈值可追溯
- **WHEN** 开发者需要调整某个指标的合理性阈值
- **THEN** 仅需修改 `snapshot_builder.py` 中对应的常量定义，无需全文搜索魔数
