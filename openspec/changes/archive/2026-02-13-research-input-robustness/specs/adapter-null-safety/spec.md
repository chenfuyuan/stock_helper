## ADDED Requirements

### Requirement: Adapter 层 daily 空值防护
当 `GetStockBasicInfoUseCase` 返回的 `StockBasicInfoDTO.daily` 为 `None` 时（标的存在但无最新日线数据），数据适配器 SHALL 返回 `None`（表示"数据不可用"），而非抛出 `AttributeError`。
受影响的适配器：`ValuationDataAdapter`、`MacroDataAdapter`。

#### Scenario: 估值适配器遇到 daily 为 None
- **WHEN** `ValuationDataAdapter.get_stock_overview(symbol)` 被调用，且 `GetStockBasicInfoUseCase` 返回的 `StockBasicInfoDTO` 中 `daily` 为 `None`
- **THEN** 方法 SHALL 返回 `None`，且记录 WARNING 级别日志说明该标的缺少日线数据

#### Scenario: 宏观适配器遇到 daily 为 None
- **WHEN** `MacroDataAdapter.get_stock_overview(symbol)` 被调用，且 `GetStockBasicInfoUseCase` 返回的 `StockBasicInfoDTO` 中 `daily` 为 `None`
- **THEN** 方法 SHALL 返回 `None`，且记录 WARNING 级别日志说明该标的缺少日线数据

#### Scenario: daily 正常时行为不变
- **WHEN** `ValuationDataAdapter.get_stock_overview(symbol)` 或 `MacroDataAdapter.get_stock_overview(symbol)` 被调用，且 `daily` 不为 `None`
- **THEN** 方法 SHALL 正常返回 `StockOverviewInput` 或 `MacroStockOverview`，行为与当前一致

---

### Requirement: Catalyst 适配器异常捕获收窄
`CatalystDataAdapter.get_stock_overview()` 的 `except Exception` SHALL 收窄为仅捕获预期的数据查询异常（如 `SQLAlchemyError` 或自定义的数据层异常），非预期异常（如 `TypeError`、`ValueError`、配置错误）SHALL 向上抛出，避免掩盖系统级故障。

#### Scenario: 数据查询异常被优雅处理
- **WHEN** `CatalystDataAdapter.get_stock_overview(symbol)` 内部的 `GetStockBasicInfoUseCase` 抛出数据库连接异常
- **THEN** 方法 SHALL 记录 ERROR 日志并返回 `None`

#### Scenario: 非预期异常不被吞掉
- **WHEN** `CatalystDataAdapter.get_stock_overview(symbol)` 内部发生 `TypeError` 或 `AttributeError` 等编程错误
- **THEN** 异常 SHALL 向上传播，不被 `except` 捕获

---

### Requirement: third_code 取值来源统一
所有数据适配器在构建 stock overview 时，`third_code` 的取值来源 SHALL 统一。当 `daily` 可用时优先从 `daily.third_code` 取值（最新交易日维度），当 `daily` 不可用时回退到 `info.third_code`。

#### Scenario: daily 可用时使用 daily.third_code
- **WHEN** 适配器构建 stock overview 且 `daily` 不为 `None`
- **THEN** `third_code` SHALL 取自 `daily.third_code`

#### Scenario: daily 不可用时回退到 info.third_code
- **WHEN** 适配器构建 stock overview 且 `daily` 为 `None`（本需求仅适用于 Catalyst 适配器，因为估值/宏观适配器在 daily 为 None 时直接返回 None）
- **THEN** `third_code` SHALL 取自 `info.third_code`
