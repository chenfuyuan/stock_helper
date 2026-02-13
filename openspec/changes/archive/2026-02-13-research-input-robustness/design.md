## Context

Research 模块的五个专家（技术分析师、财务审计员、估值建模师、宏观情报员、催化剂侦探）各自通过 Infrastructure Adapter 从 `data_engineering` / `llm_platform` 获取数据，经 Snapshot Builder 预计算后传入 Agent Adapter 填充 Prompt、调用 LLM。当前实现在 happy path 下运行良好，但在以下边界场景存在防御性不足：

1. `StockBasicInfoDTO.daily` 为 `Optional[StockDaily]`，但估值/宏观适配器未做 `None` 检查
2. 技术指标计算在数据不足时返回 0.0/50.0 等合法但误导性的默认值
3. 五个专家在异常类型、返回类型、默认值上存在不一致
4. 估值快照构建器对上游财务指标（毛利率、ROE 等）直接透传，不做合理性校验——实际案例中出现 44,969,179.57% 的毛利率直接传入 LLM Prompt

本变更是纯**防御性加固**，不改变任何正常流程的行为，仅修复边界/极端场景的鲁棒性。

## Goals / Non-Goals

**Goals:**
- 消除 `daily=None` 导致的 `AttributeError` 崩溃风险
- 让 LLM 收到的技术指标输入在数据不足时具有明确的"无数据"标记
- 统一五个专家的异常类型和返回值契约，降低 Coordinator 侧的兼容成本
- 补充必要的边缘场景校验（数据量门槛、参数范围）
- 在估值快照构建阶段拦截明显异常的财务指标值，防止 LLM 在脏数据上做分析

**Non-Goals:**
- 不修改 Prompt 模板的分析逻辑或 LLM 输出结构
- 不修改 `data_engineering` 模块的返回结构
- 不引入新的 Port 接口或改变模块间依赖关系
- 不做性能优化
- 不修复上游数据源本身的数据质量问题（那是 `data_engineering` 的职责）

## Decisions

### Decision 1：Adapter 层 daily 空值处理策略

**选择**：在 `_to_stock_overview()` 和 `MacroDataAdapter.get_stock_overview()` 入口处检查 `basic_info.daily is None`，若为 `None` 则返回 `None`，让上游 Service 层复用已有的 `if overview is None: raise BadRequestException(...)` 逻辑。

**替代方案 A**：在 `GetStockBasicInfoUseCase` 中保证 `daily` 非 `None`——拒绝，因为这会改变 `data_engineering` 模块的契约（`daily` 为 `None` 是合法的语义：标的存在但无日线数据）。

**替代方案 B**：在适配器中构造一个全 `None` 值的 `StockOverviewInput`——拒绝，因为 `current_price` 等字段为 `float` 非 `Optional[float]`，填入 `None` 会违反 Pydantic 校验。

**具体变更点**：
- `valuation_data_adapter.py` → `_to_stock_overview()` 上方增加 `if basic_info_result.daily is None: return None`，`get_stock_overview()` 中对应处理
- `macro_data_adapter.py` → `get_stock_overview()` 中增加 `if basic_info.daily is None` 检查

### Decision 2：技术指标不足时的标记策略

**选择**：将 `TechnicalIndicatorsSnapshot` 中的数值型指标字段从 `float` 改为 `Optional[float]`（默认 `None`）；`calculator.py` 中数据不足时返回 `None`；`fill_user_prompt()` 在填充模板时将 `None` 转为字符串 `"N/A"`。

**替代方案**：在 Snapshot 中使用 `PlaceholderValue`（`float | str`）类似财务/估值快照的做法——可行但技术指标 DTO 当前全是 `float`，改为联合类型会影响下游做数值计算的可能性。`Optional[float]` 更语义化：`None` 明确表示"无法计算"。

**具体变更点**：
- `domain/dtos/indicators_snapshot.py`：数值型字段改为 `Optional[float] = None`
- `infrastructure/indicators/calculator.py`：各指标函数数据不足时返回 `None`；`compute_technical_indicators()` 中条件赋值
- `infrastructure/prompt_loader.py` → `fill_user_prompt()`：对 `None` 值做 `"N/A"` 转换

### Decision 3：CatalystDetectiveService 返回值归一化

**选择**：在 `CatalystDetectiveService.run()` 内部完成 `CatalystDetectiveAgentResult → dict[str, Any]` 转换，使其返回签名与其他四个专家一致（`dict[str, Any]`）。同时删除 `ResearchGatewayAdapter._normalize_catalyst_result()`。

**替代方案**：保持现状，由 Coordinator 侧做归一化——拒绝，因为这让 Service 契约不一致，增加 Coordinator 的耦合度。

**具体变更点**：
- `application/catalyst_detective_service.py`：`run()` 返回类型改为 `dict[str, Any]`，内部解构 `CatalystDetectiveAgentResult`
- `coordinator/infrastructure/adapters/research_gateway_adapter.py`：删除 `_normalize_catalyst_result()`，催化剂分支直接返回 `svc.run()` 结果

### Decision 4：异常类型统一策略

**选择**：`CatalystDetectiveService` 中的 `StockNotFoundError` → `BadRequestException`，`CatalystSearchError` → `BadRequestException`。保留 `domain/exceptions.py` 中的自定义异常类定义（避免影响其他潜在调用方），但 Service 层不再使用它们。

**理由**：其他四个专家已统一使用 `BadRequestException`，Coordinator 的全局异常处理中间件按 `AppException` 体系处理。保持一致降低维护成本。

### Decision 5：最低 K 线数量常量放置

**选择**：在 `TechnicalAnalystService` 中定义模块常量 `MIN_BARS_REQUIRED = 30`，在 `run()` 中校验。

**理由**：30 根 K 线 ≈ 6 周交易日，是计算 MACD(26)、布林带(20) 等核心指标的最低合理门槛。该常量属于 Application 层的业务规则，不放在 Infrastructure 的 `calculator.py` 中。

### Decision 6：财务指标合理性校验策略

**选择**：在 `ValuationSnapshotBuilderImpl.build()` 中，对从 `FinanceRecordInput` 提取的关键财务指标进行合理性边界校验。超出合理范围的值替换为 `"N/A"`（`PlaceholderValue` 类型兼容），并记录 WARNING 日志。

**校验位置**：Infrastructure 层的 `snapshot_builder.py`——这是从"原始财务数据"到"LLM 可消费的快照"的转换层，是最合适的防御点。不在 Domain DTO（`FinanceRecordInput`）上加校验，因为 Domain DTO 的职责是忠实映射上游数据结构。

**阈值常量定义**（以模块级常量集中定义，避免魔数）：

| 指标 | 常量名 | 有效范围 | 理由 |
|------|--------|---------|------|
| 毛利率 | `GROSS_MARGIN_BOUNDS` | [-100, 100] | 毛利率 = (营收-成本)/营收，理论上限 ±100% |
| ROE | `ROE_BOUNDS` | [-500, 500] | 极端高杠杆+亏损时可大，但 >500% 必为脏数据 |
| 净利率 | `NET_MARGIN_BOUNDS` | [-1000, 1000] | 微营收公司可能极端，但万倍不可能 |
| 资产负债率 | `DEBT_RATIO_BOUNDS` | [0, 300] | 资不抵债时可 >100%，但 >300% 极不可能 |

**替代方案 A**：在 `FinanceRecordInput`（Domain DTO）的 Pydantic validator 中做校验——拒绝。Domain DTO 的职责是忠实映射上游数据。如果在 DTO 层拦截，Adapter 构造 DTO 时就会抛 `ValidationError`，影响整个 Service 流程（可能导致该标的完全无法分析，而非"部分指标标记为 N/A 继续分析"）。

**替代方案 B**：在 `data_engineering` 模块的查询接口中做校验——拒绝。这是跨模块边界的侵入，且不同消费方对"合理范围"的定义可能不同（research 模块是为 LLM 消费，对异常值更敏感）。

**对 `_calculate_gross_margin_trend()` 的加固**：在趋势计算函数内增加对两期毛利率基础值的合理性检查，若任一期超出 `GROSS_MARGIN_BOUNDS` 则返回 `"N/A"`，避免产生"同比上升 5,502,560.9%"这样的荒谬描述。

## Risks / Trade-offs

- **[Risk] `Optional[float]` 改动影响面较大** → 仅改 `TechnicalIndicatorsSnapshot` 内部字段，对外通过 Prompt 填充时已转为字符串，不影响 Prompt 模板结构和 LLM 输出格式。需确保 `snapshot.model_dump()` 序列化时 `None` → `null` 在存储/日志中可接受。
- **[Risk] 催化剂 Service 返回类型变更** → `ResearchGatewayAdapter` 是唯一调用方，改动范围可控。需同步更新 Coordinator 侧代码和相关测试。
- **[Risk] 合理性阈值的误判风险** → 阈值设置偏宽（如 ROE ±500%），可能仍有极端但合法的值被放过。但本次目标是拦截"明显脏数据"（如 4500 万% 的毛利率），而非精细筛选。阈值可根据实际运行中的 WARNING 日志反馈逐步调优。
- **[Trade-off] 异常类型仍保留自定义异常定义** → 虽然 Service 不再使用，但未来如需更精细的异常分类可复用。删除它们是可选的清理工作，不纳入本次变更。
- **[Trade-off] 合理性校验仅覆盖估值快照** → 财务审计员的 `FinancialSnapshotDTO` 也可能受类似的上游数据质量影响，但本次仅修复估值建模师路径（已有真实案例），财务审计员路径可作为后续独立 change。
