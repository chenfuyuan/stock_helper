# Spec: research-error-consistency

统一五个专家 Application Service 的异常类型、返回值类型与默认值规范，降低 Coordinator 侧的兼容处理成本。涉及 CatalystDetectiveService、FinancialAuditorService、ValuationModelerService 及 ResearchGatewayAdapter。

**测试约定**：每个 `#### Scenario:` 在变更**交付时**须对应至少一个自动化测试用例（单元或集成）；实现顺序可先实现再补测，以完整测试通过为需求完成标准。

---

## Requirements

### Requirement: 异常类型统一
五个专家 Application Service 在遇到"标的不存在"或"搜索全部失败"等业务异常时，SHALL 统一使用 `BadRequestException`（来自 `src/shared/domain/exceptions.py`），不使用各模块自定义的 `StockNotFoundError`、`CatalystSearchError` 等。保持 Coordinator 侧异常捕获的一致性。

#### Scenario: 催化剂侦探标的不存在
- **WHEN** `CatalystDetectiveService.run(symbol)` 发现标的不存在
- **THEN** SHALL 抛出 `BadRequestException`（而非当前的 `StockNotFoundError`），message 中包含 symbol 信息

#### Scenario: 催化剂侦探搜索全部失败
- **WHEN** `CatalystDetectiveService.run(symbol)` 发现四个维度搜索结果全为空
- **THEN** SHALL 抛出 `BadRequestException`（而非当前的 `CatalystSearchError`），message 中说明搜索失败原因

#### Scenario: 其他四个专家异常类型不变
- **WHEN** 技术分析师、财务审计员、估值建模师、宏观情报员遇到业务异常
- **THEN** SHALL 继续使用 `BadRequestException`，行为与当前一致

---

### Requirement: 返回值类型统一
所有五个专家 Application Service 的 `run()` 方法 SHALL 统一返回 `dict[str, Any]`。`CatalystDetectiveService.run()` SHALL 在内部完成 `CatalystDetectiveAgentResult` → `dict` 的转换，而非将转换责任推给 Coordinator 侧。

#### Scenario: 催化剂侦探返回 dict
- **WHEN** `CatalystDetectiveService.run(symbol)` 执行成功
- **THEN** SHALL 返回 `dict[str, Any]`（而非当前的 `CatalystDetectiveAgentResult`），包含与其他专家一致的 `input`、`output` 字段结构

#### Scenario: Coordinator 侧简化
- **WHEN** `ResearchGatewayAdapter.run_expert()` 调度催化剂侦探
- **THEN** 不再需要调用 `_normalize_catalyst_result()` 做额外归一化处理，直接使用返回的 `dict`

---

### Requirement: industry 默认值统一
当 `StockInfo.industry` 为 `None` 时，所有适配器 SHALL 统一使用 `"未知行业"` 作为默认值（中文，与宏观/估值适配器一致），不使用英文 `"Unknown"`。

#### Scenario: Catalyst 适配器 industry 为 None
- **WHEN** `CatalystDataAdapter.get_stock_overview(symbol)` 获取到的 `info.industry` 为 `None`
- **THEN** 返回的 `CatalystStockOverview.industry` SHALL 为 `"未知行业"`（而非当前的 `"Unknown"`）

#### Scenario: 其他适配器行为不变
- **WHEN** `ValuationDataAdapter` 或 `MacroDataAdapter` 获取到的 `info.industry` 为 `None`
- **THEN** 对应 overview 的 `industry` SHALL 为 `"未知行业"`，行为与当前一致

---

### Requirement: 估值历史数据为空时日志警告
`ValuationModelerService.run()` 在获取历史估值日线后，如果结果为空列表，SHALL 记录 WARNING 级别日志，告知该标的无历史估值日线数据，分位点分析将全部为 N/A。流程 SHALL 继续执行（不中断），因为即使无分位点数据，其他估值模型（PEG、Graham）仍可产出结论。

#### Scenario: 历史估值日线为空
- **WHEN** `ValuationModelerService.run()` 获取到空的 `historical_valuations` 列表
- **THEN** SHALL 记录 WARNING 日志（包含 symbol 和时间范围），然后继续执行 snapshot 构建和 Agent 调用

#### Scenario: 历史估值日线非空
- **WHEN** `ValuationModelerService.run()` 获取到非空的 `historical_valuations` 列表
- **THEN** 不记录额外 WARNING 日志，行为与当前一致

---

### Requirement: 财务审计员 limit 参数范围校验
`FinancialAuditorService.run()` SHALL 校验 `limit` 参数的有效范围（1 ≤ limit ≤ 20）。超出范围时 SHALL 抛出 `BadRequestException`，而非静默返回空数据。

#### Scenario: limit 为 0 或负数
- **WHEN** `FinancialAuditorService.run(symbol, limit=0)` 或 `limit=-1` 被调用
- **THEN** SHALL 抛出 `BadRequestException`，message 中说明 limit 的有效范围

#### Scenario: limit 超过上限
- **WHEN** `FinancialAuditorService.run(symbol, limit=100)` 被调用
- **THEN** SHALL 抛出 `BadRequestException`，message 中说明 limit 的有效范围

#### Scenario: limit 在有效范围内
- **WHEN** `FinancialAuditorService.run(symbol, limit=5)` 被调用
- **THEN** 行为与当前一致，正常获取财务数据
