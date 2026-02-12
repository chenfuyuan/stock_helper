# Design: Research 模块 — 估值建模师

## Context

Research 是愿景中的「事实工厂」Bounded Context，代码库中已存在（`src/modules/research/`），其中**技术分析师**与**财务审计员**能力已实现并通过验收。本变更是 Research 的第三个子能力：**估值建模师**，负责剥离市场情绪，仅基于基本面数据与预计算估值模型（历史分位点、PEG、格雷厄姆数字），计算标的的「内在价值」与「安全边际」，输出结构化的估值判断（Undervalued / Fair / Overvalued + 内在价值区间），供后续 Debate/Judge 使用。

**与财务审计员的核心差异**：
- 财务审计员仅消费**财务指标**数据（`StockFinance`），进行 5D 审计评分。
- 估值建模师需要**三类数据**：股票基础信息（名称/行业）、市场估值数据（PE/PB/PS/价格/市值 + 历史时序）、以及部分财务指标（EPS/BPS/ROE/毛利率等）。
- 估值建模师的核心特点是**预计算**：所有估值模型（分位点、PEG、Graham Number、Safety Margin）在代码中完成，LLM 仅做定性解读，**禁止自行计算**。

**约束**：模块间调用必须通过被调用模块的 **Application 接口**，不得直接依赖对方领域模型或 Infrastructure。Research 依赖 data_engineering（股票信息、市场行情、财务指标）、llm_platform（LLM）。

**已有资产**：
- 技术分析师与财务审计员已建立的模块骨架（domain/ports、application、infrastructure/adapters、agents/ 结构），可复用 `ILLMPort`、`prompt_loader` 加载模式、以及 Domain 异常（`LLMOutputParseError`）等公共设施。
- 已有 `FinanceRecordInput` DTO 与 `FinancialDataAdapter`（可复用其 DTO 结构，需扩展 `bps` 字段）。
- 估值建模师的 System Prompt 与 User Prompt 模板**已预先定义**（见 `system.md` 与 `user.md`）。

**相关方**：Coordinator（未来编排 Research）、Debate/Judge（消费 ResearchReport）；本变更仅实现估值建模师单元，不实现编排与报告聚合。

**测试约束**：Spec 中每个 Scenario 在交付时须有对应自动化测试；实现顺序灵活（可先实现再补测）。设计决策须考虑可测性（Port、DI、DTO），便于补测或按需 TDD。

## Goals / Non-Goals

**Goals:**

- 在 `src/modules/research/` 下新增估值建模师能力，复用已有模块骨架与公共设施（`ILLMPort`、prompt 加载模式、`LLMOutputParseError`）。
- 估值建模师通过 **Application 接口** 调用 data_engineering（获取股票信息、市场行情、财务指标）、llm_platform（LLM 调用），不直接依赖其 Domain/Infrastructure。
- 输入：股票代码（symbol）；系统自动获取股票基础信息、最新市场估值数据、历史估值时序数据（用于分位点）、财务指标数据。在 Research 内部预计算：PE/PB/PS 历史分位点、PEG 比率、格雷厄姆数字与安全边际、毛利率趋势。输出：固定结构 JSON（valuation_verdict、confidence_score、estimated_intrinsic_value_range、key_evidence、risk_factors、reasoning_summary）。
- 对外暴露独立 Application 入口（`ValuationModelerService`），与技术分析师/财务审计员接口形态一致但各自独立。若提供 HTTP 接口，响应体 SHALL 包含 input、output、valuation_indicators（代码塞入的估值快照，与 technical_indicators / financial_indicators 结构对称）。
- **可测性**：通过 Port 抽象与依赖注入，使 Application 层在无真实下游时可仅用 mock 验证行为；每个 Spec Scenario 可映射为可执行测试。

**Non-Goals:**

- 不实现 Coordinator、Debate、Judge；不实现 Research 的「并行五专家」编排与完整 ResearchReport 聚合。
- 不实现其余两专家（宏观情报员、催化剂侦探）。
- 不改变技术分析师与财务审计员的现有实现。
- 不实现市场行情的外部拉取/同步（data_engineering 已有同步能力），仅新增只读查询。

## Decisions

### 1. 数据来源与 data_engineering 查询接口

- **选择**：估值建模师需要三类数据，分别来自 data_engineering 的不同 Application 接口：

  | 数据类别 | data_engineering 接口 | 状态 |
  |----------|----------------------|------|
  | 股票基础信息 + 最新行情 | `GetStockBasicInfoUseCase` → `StockBasicInfoDTO(info: StockInfo, daily: StockDaily)` | **已有**。返回 StockInfo（name、industry）+ 最新 StockDaily（close、pe_ttm、pb、ps_ttm、dv_ratio、total_mv）。 |
  | 历史估值日线 | `GetValuationDailiesForTickerUseCase` → `List[ValuationDailyDTO]` | **新增**。按 third_code + date range 返回含估值字段（trade_date、close、pe_ttm、pb、ps_ttm）的日线记录，供 Research 计算分位点。当前 `DailyBarDTO` 仅含 OHLCV，不暴露估值字段。 |
  | 财务指标 | `GetFinanceForTickerUseCase` → `List[FinanceIndicatorDTO]` | **已有**，需**扩展**：在 `FinanceIndicatorDTO` 中新增 `bps`（每股净资产）字段。Graham Number 计算需要 EPS + BPS。 |

  **新增 `GetValuationDailiesForTickerUseCase`**：
  1. `IMarketQuoteRepository` 增加读方法 `get_valuation_dailies(third_code: str, start_date: date, end_date: date) -> List[StockDaily]`，返回指定区间的日线记录。
  2. 新增 Application 查询用例 `GetValuationDailiesForTickerUseCase`（入参 ticker + start_date + end_date，出参 `ValuationDailyDTO` 列表），遵循 `GetDailyBarsForTickerUseCase` 的已有模式。
  3. `ValuationDailyDTO` 仅包含估值分析所需字段：`trade_date`、`close`、`pe_ttm`、`pb`、`ps_ttm`、`dv_ratio`、`total_mv`。

  **扩展 `FinanceIndicatorDTO`**：
  1. 在 `FinanceIndicatorDTO` 中新增 `bps: Optional[float] = None` 字段。
  2. 在 `GetFinanceForTickerUseCase` 的 DTO 转换中映射 `StockFinance.bps → FinanceIndicatorDTO.bps`。
  3. 在 Research 的 `FinanceRecordInput` 中同步新增 `bps: Optional[float] = None` 字段，`FinancialDataAdapter` 映射时传递该字段。

- **理由**：遵循已有查询模式（对齐 `GetDailyBarsForTickerUseCase` / `GetFinanceForTickerUseCase`）；Repository 读方法放在 Domain Port，实现在 Infrastructure，符合依赖倒置。`ValuationDailyDTO` 仅暴露估值字段（不含全部 StockDaily 字段），遵循最小暴露原则。

### 2. Domain 层三个抽象与跨模块调用

- **选择**：Research Domain 层包含三类与估值建模师相关的抽象：

  1. **获取估值所需数据**：Port（`IValuationDataPort`），包含三个方法：
     - `get_stock_overview(symbol) -> StockOverviewInput`：获取股票基础信息 + 最新市场估值数据。Adapter 内部调用 `GetStockBasicInfoUseCase`，将 StockInfo + StockDaily 转为 Research 内部 DTO。返回 `StockOverviewInput`，含 stock_name、industry、third_code、current_price、total_mv、pe_ttm、pb、ps_ttm、dv_ratio。
     - `get_valuation_dailies(ticker, start_date, end_date) -> List[ValuationDailyInput]`：获取历史估值日线。Adapter 内部调用新增的 `GetValuationDailiesForTickerUseCase`。返回 `ValuationDailyInput`，含 trade_date、close、pe_ttm、pb、ps_ttm。
     - `get_finance_for_valuation(ticker, limit) -> List[FinanceRecordInput]`：获取财务指标。Adapter 内部调用 `GetFinanceForTickerUseCase`，将 DTO 转为 Research 的 `FinanceRecordInput`（含 bps 字段）。复用已有的 `FinanceRecordInput` 结构。
  2. **构建估值快照**：Port（`IValuationSnapshotBuilder`），入参为 `StockOverviewInput` + `List[ValuationDailyInput]` + `List[FinanceRecordInput]`，出参为 `ValuationSnapshotDTO`（与 User Prompt 模板占位符一一对应）。**预计算逻辑在 Infrastructure 层实现**（见 Decision 4）。
  3. **估值分析**：Port（`IValuationModelerAgentPort`），入参为 `ValuationSnapshotDTO`，出参为 `ValuationModelAgentResult`（含解析后的 `ValuationResultDTO` + 原始 LLM 输出 + user prompt）。实现层负责加载/填充 Prompt、调用 LLM、解析结果。

  跨模块时，Research 的 Infrastructure Adapter 仅通过 data_engineering 的 **Application 接口** 获取数据，不引用对方 domain 或 infrastructure。

- **理由**：与财务审计员保持一致的三层 Port 模式（数据获取 → 数据处理/预计算 → Agent 分析），Domain 只定义「做什么」的契约，实现在 Infrastructure；Application 编排仅依赖 Domain Port，符合依赖倒置与可测性。估值建模师的 `IValuationDataPort` 有 3 个方法（而非单一方法），因为数据来源更多元，但保持"数据获取"这一关注点在同一个 Port 中，避免 Service 注入过多依赖。

### 3. Research 对 Coordinator 暴露的 Application 接口：按专家独立、不共用

- **选择**：延续技术分析师与财务审计员的模式。本变更对外仅暴露估值建模师专属入口 `ValuationModelerService.run(symbol)`。Coordinator 编排时分别调用各专家的 Application 接口。**Application 与 HTTP 响应体**：返回结果 SHALL 包含解析后的估值 DTO 及 input、output、valuation_indicators（代码塞入），与技术分析师的 technical_indicators、财务审计员的 financial_indicators 结构对称。
- **理由**：每个专家入参/出参与职责不同，独立接口便于契约清晰、单独编写测试与演进。

### 4. 估值快照构建的预计算逻辑

- **选择**：`IValuationSnapshotBuilder` 的 Infrastructure 实现将原始数据转为 `ValuationSnapshotDTO`，具体预计算逻辑：

  1. **历史分位点**：取 `List[ValuationDailyInput]`（约 3 年交易日数据），计算当前 PE-TTM、PB、PS-TTM 在历史序列中的百分位排名。算法：`percentile = (当前值在有效序列中的排名 / 有效序列长度) × 100`，跳过 None / 负值 / 异常值。数据不足（如历史记录 < 60 个交易日）时标记 N/A。
  2. **PEG 比率**：`PEG = PE-TTM / growth_rate_avg`。其中 `growth_rate_avg` 为最近 4 季度利润 YoY 增速的平均值（由财务数据计算）。增速为 0 或负时 PEG 标记 N/A。
  3. **格雷厄姆数字**：`Graham = sqrt(22.5 × EPS × BPS)`。EPS 或 BPS 为负/零/None 时标记 N/A。
  4. **安全边际**：`Safety Margin = (Graham Value - Current Price) / Current Price × 100`。Graham 为 N/A 时安全边际也标记 N/A。
  5. **毛利率趋势**：比较最新期与上一期 gross_margin，输出趋势描述（如"同比上升 x%"/"同比下降 x%"/"持平"）；仅 1 期数据时标记 N/A。
  6. **ROE 取值**：使用 `roe_waa`（加权平均净资产收益率）作为 User Prompt 中的 `roe` 字段。
  7. 输出 `ValuationSnapshotDTO`，各字段与 User Prompt 模板占位符一一对应。

- **理由**：所有数值计算在代码中完成，LLM 仅做定性解读——这是估值建模师 Prompt 的核心约束（"No Math"）。将预计算逻辑封装在 Infrastructure 实现中，通过 Domain Port 暴露，Application 不关心计算细节；便于测试（mock Port 返回固定快照）与后续调整模型参数。

### 5. Prompt 资源复用已有模式

- **选择**：估值建模师的 System Prompt 与 User Prompt 模板存放在 `src/modules/research/agents/valuation_modeler/prompts/`（`system.md` 与 `user.md`），运行时通过与财务审计员相同的加载模式读取。在 `prompt_loader.py` 中新增估值建模师的加载与填充函数。User Prompt 使用 `{...}` 单花括号占位符（Python `str.format()` 风格），与财务审计员和技术分析师一致。**Prompt 内容已预先定义**，实现时直接从 `openspec/changes/research-valuation-modeler/` 下的 `system.md` 与 `user.md` 拷贝至资源目录。
- **理由**：复用已有 prompt 加载基础设施模式，避免重复建设；占位符风格与已有专家统一，使用 `str.format()` 填充。

### 6. LLM 调用与输出解析

- **选择**：复用已有 `ILLMPort`（llm_platform 的 `LLMService.generate`）传入 System Prompt 与填充后的 User Prompt；要求模型仅输出纯 JSON。**估值建模师的 JSON 结构与其他专家不同**，解析逻辑内聚到 `agents/valuation_modeler/output_parser.py`。Domain 层定义输出 DTO（`ValuationResultDTO`），包含：
  - `valuation_verdict`：Literal（"Undervalued (低估)" / "Fair (合理)" / "Overvalued (高估)"）
  - `confidence_score`：float（0.0–1.0），基于证据一致性
  - `estimated_intrinsic_value_range`：嵌套对象（`lower_bound: str`、`upper_bound: str`）
  - `key_evidence`：list[str]（证据列表，须引用输入数据）
  - `risk_factors`：list[str]（风险列表）
  - `reasoning_summary`：str（专业精炼总结，须解释是机会还是陷阱）

  解析失败时记录日志（含 LLM 原始输出，可截断）并抛出 `LLMOutputParseError`。输出解析器复用 `_strip_thinking_tags`（剥离 `<think>` 标签）和 markdown 代码块剥离逻辑。

- **理由**：各 Agent 返回的 JSON 结构不同，解析内聚到 Agent 可避免共享解析层膨胀；复用已有领域异常；单元测试可针对 output_parser 单独测。

### 7. 目录与分层结构

- **选择**：在 `src/modules/research/` 已有结构上扩展：
  - **domain/valuation_dtos.py**：新增 `ValuationResultDTO`、`IntrinsicValueRangeDTO`、`ValuationModelAgentResult`。
  - **domain/ports/dto_valuation_inputs.py**：新增 `StockOverviewInput`、`ValuationDailyInput`、`ValuationSnapshotDTO`。
  - **domain/ports/valuation_data.py**：`IValuationDataPort`（3 个方法）。
  - **domain/ports/valuation_snapshot_builder.py**：`IValuationSnapshotBuilder`。
  - **domain/ports/valuation_modeler_agent.py**：`IValuationModelerAgentPort`。
  - **domain/ports/dto_financial_inputs.py**：`FinanceRecordInput` 新增 `bps` 字段（向后兼容）。
  - **application/valuation_modeler_service.py**：编排「校验 → 获取数据 → 构建快照 → 调用 Agent → 返回完整响应」。
  - **infrastructure/adapters/valuation_data_adapter.py**：实现 `IValuationDataPort`（内部调用 3 个 data_engineering Application 接口）。
  - **infrastructure/adapters/valuation_modeler_agent_adapter.py**：实现 `IValuationModelerAgentPort`（加载 Prompt + 调用 LLM + 解析）。
  - **infrastructure/valuation_snapshot/snapshot_builder.py**：实现 `IValuationSnapshotBuilder`（预计算分位点、PEG、Graham 等）。
  - **agents/valuation_modeler/prompts/**：`system.md`、`user.md`。
  - **agents/valuation_modeler/output_parser.py**：解析 LLM JSON 输出。
  - **presentation/rest/valuation_modeler_routes.py**：估值建模师 REST 路由，通过 FastAPI `Depends` 装配 `ValuationModelerService` 所需的全部 Port 实现，处理异常（BadRequestException→400、LLMOutputParseError→422、其他→500），与 `financial_auditor_routes.py` 和 `technical_analyst_routes.py` 同级同模式。
- **理由**：与技术分析师、财务审计员的已有目录模式一致；各专家的 Port、Adapter、Agent 目录独立，互不干扰。

### 8. 复用已有 FinanceRecordInput 与适配

- **选择**：在已有 `FinanceRecordInput` 中新增 `bps: Optional[float] = None` 字段（向后兼容，不破坏财务审计员的现有逻辑）。同时在 `FinancialDataAdapter._to_finance_record` 映射中添加 `bps` 字段。估值建模师的 `IValuationDataPort.get_finance_for_valuation` 方法返回同一 `FinanceRecordInput` DTO。
- **备选**：为估值建模师创建独立的 `ValuationFinanceInput` DTO。
- **理由**：估值建模师与财务审计员消费的财务数据来自同一上游（`GetFinanceForTickerUseCase`），复用 DTO 避免重复定义；新增 Optional 字段向后兼容，不影响财务审计员。

### 9. 实现顺序与测试

- **选择**：实现顺序**灵活**：可先实现再在交付前补全测试，也可在关键逻辑处先写测试再实现。Tasks 按实现块组织（data_engineering 扩展 → Research Domain/Ports → 快照构建/预计算 → Agent + 解析 → Application 编排 → 完整测试），**最后统一做完整测试**，确保所有 Spec Scenario 有对应通过测试。
- **理由**：在保证可验证性的前提下减少步骤、加快执行；设计已考虑可测性（Port、DTO），便于补测。

## Risks / Trade-offs

| 风险 | 缓解 |
|------|------|
| LLM 返回非 JSON 或格式不稳定 | Prompt 明确要求「仅输出纯 JSON 字符串、无 Markdown 标记」；解析内聚于 `agents/valuation_modeler/output_parser.py`，try/except + 日志；**测试覆盖「解析失败」Scenario**；复用 `_strip_thinking_tags` 剥离思考过程。 |
| 历史分位点计算受 PE/PB 负值或缺失值影响 | 快照构建器在计算百分位时跳过 None / 负值 / 0 值（PE 为负通常因亏损，无估值意义）；有效数据不足时标记 N/A，不强行计算。 |
| `GetStockBasicInfoUseCase` 直接暴露 Domain 实体（StockInfo、StockDaily） | 这是 data_engineering 的已有设计问题，不属于本变更修复范围。估值数据 Adapter 仅提取所需字段转为 Research 内部 DTO，不传递 Domain 实体引用。 |
| 历史估值日线数据量可能较大（3 年 ≈ 750 条） | 分位点计算为纯内存排序 + 排名，750 条数据性能无忧；查询通过 date range 限制数据量。 |
| Graham Number 对亏损或轻资产公司无意义 | EPS/BPS 为负或零时 Graham 标记 N/A；Prompt 已明确 LLM 遇到 N/A 应声明"数据不足"而非猜测。 |
| PEG 对增速为负的公司无意义 | 增速 ≤ 0 时 PEG 标记 N/A；LLM Prompt 已有 PEG 判断标准说明。 |
| 估值建模师与财务审计员的公共设施耦合 | 二者共用 `ILLMPort`、`LLMOutputParseError`、`FinanceRecordInput`（新增 bps 向后兼容）等公共设施，但各自的 Port、Adapter、Agent、输出 DTO 完全独立；公共设施变更需考虑兼容性。 |

## Migration Plan

- **部署**：在已有 Research 模块上扩展，无存量数据迁移。data_engineering 仅新增只读查询用例（`GetValuationDailiesForTickerUseCase`）及 `FinanceIndicatorDTO` 新增 optional 字段，不修改现有写入逻辑或数据库 schema（`stock_daily` 表已存在且包含估值字段）。引入新依赖通过依赖注入在应用启动时装配。
- **回滚**：估值建模师为独立新增能力，回滚即停止调用该 Application 接口；data_engineering 新增的只读接口无副作用，可保留或移除。

## Open Questions

- 历史分位点默认使用最近 3 年（约 750 个交易日）的数据？还是允许调用方指定回溯期？初步决定默认 3 年，可通过参数覆盖。
- `estimated_intrinsic_value_range` 的 `lower_bound` / `upper_bound` 由 LLM 输出字符串（如 "基于 Graham 模型推导的 18.5 元"），还是精确数值？查看 Prompt 定义，为描述性字符串，包含推导依据。
- ~~Presentation 层（REST 路由）是否在本变更中实现？~~ **已确认：必须实现**。路由位于 `presentation/rest/valuation_modeler_routes.py`，与技术分析师/财务审计员同级同模式。
