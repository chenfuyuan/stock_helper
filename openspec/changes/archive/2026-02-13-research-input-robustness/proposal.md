## Why

Research 模块五个专家的输入参数流水线存在**防御性不足**的问题，经审查发现：

1. **Adapter 空值崩溃**：`StockBasicInfoDTO.daily` 为 `None` 时会导致估值建模师和宏观情报员适配器产生 `AttributeError` 崩溃。
2. **技术指标误导性默认值**：技术分析师在数据量不足时返回 0.0 或 50.0 等"合法但误导性"默认值，LLM 无法区分"真实计算结果"与"数据不足的默认值"。
3. **异常与返回值不一致**：五个专家在异常类型、返回值类型和 `industry` 默认值上存在不一致，增加 Coordinator 和下游模块的处理成本。
4. **财务指标无合理性校验**：估值建模师的 `ValuationSnapshotBuilder` 对上游财务数据（毛利率、ROE 等）直接透传，不做任何合理性边界检查。实际案例：万向德农（600371.SH）的毛利率被传入为 44,969,179.57%（显然是上游数据质量问题），导致 LLM 收到的 Prompt 中出现"毛利率: 44969179.57%"及"同比上升 5502560.9%"的异常数据，严重干扰分析结论的可信度。

这些问题在极端/边界场景下会导致崩溃或分析质量严重下降，需要系统性修复。

## What Changes

- **修复 Adapter 空值崩溃**：在 `ValuationDataAdapter._to_stock_overview()` 和 `MacroDataAdapter.get_stock_overview()` 中，对 `basic_info.daily` 为 `None` 的情况做防御处理；收窄 `CatalystDataAdapter.get_stock_overview()` 的 `except Exception` 范围，避免吞掉非预期异常。
- **技术指标数据量门槛与标记改进**：在 `TechnicalAnalystService.run()` 中新增最低 K 线数量校验（建议 ≥ 30 根）；将指标不足时的 RSI、KDJ 等默认值从 50.0 改为 `None`（或显式 N/A），让 LLM 能明确区分"无数据"与"中性值"。
- **统一异常与返回值规范**：所有五个专家的 Application Service 使用一致的异常类型（统一使用 `BadRequestException` 或语义化领域异常）、一致的返回类型（`dict[str, Any]`），以及一致的 `industry` 默认值（`"未知行业"`）。
- **补充边缘场景校验**：估值建模师的 `historical_valuations` 为空时给出日志警告；财务审计员的 `limit` 参数做范围校验。
- **财务指标合理性校验**：在 `ValuationSnapshotBuilderImpl.build()` 中增加关键财务指标的合理性边界检查（毛利率、ROE、净利率、资产负债率），超出合理范围的值置为 `N/A` 并记录 WARNING 日志；同时加固毛利率趋势计算，在基础值异常时返回 `N/A`。

## Capabilities

### New Capabilities
- `adapter-null-safety`: 修复数据适配器层的空值崩溃风险——对 `StockBasicInfoDTO.daily` 做 `None` 防护，收窄异常捕获范围，统一 `third_code` 取值来源
- `indicator-data-sufficiency`: 为技术指标计算增加数据量门槛校验，改进数据不足时的标记策略（从误导性默认值改为显式 N/A），确保 LLM 收到的输入可靠
- `research-error-consistency`: 统一五个专家 Application Service 的异常类型、返回值类型与默认值规范，降低 Coordinator 侧的兼容处理成本
- `financial-data-sanity`: 在估值快照构建阶段增加财务指标合理性校验，拦截上游数据异常（如毛利率 4500 万%），防止 LLM 在异常输入上产生不可靠的分析结论

### Modified Capabilities
（无需修改已有 spec 的行为要求）

## Impact

- **受影响代码**：`src/modules/research/` 下的 `application/`（5 个 Service）、`infrastructure/adapters/`（5 个 Adapter）、`infrastructure/indicators/calculator.py`、`domain/dtos/indicators_snapshot.py`、`infrastructure/valuation_snapshot/snapshot_builder.py`
- **受影响 API**：无新增/删除 API，现有 5 个专家接口的错误响应语义可能变化（更精确的错误信息）
- **向后兼容**：Prompt 模板（`user.md`）可能需微调以适配指标 N/A 标记的变化；Coordinator 侧 `ResearchGatewayAdapter._normalize_catalyst_result()` 在返回值统一后可简化；估值快照中部分原本透传的异常值将被替换为 N/A
- **测试**：需覆盖 `daily=None`、K 线不足（<30 根）、空估值日线、`limit=0`、毛利率异常值等边界场景
