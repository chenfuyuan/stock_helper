# Design: Research 模块 — 财务审计员

## Context

Research 是愿景中的「事实工厂」Bounded Context，代码库中已存在（`src/modules/research/`），其中**技术分析师**能力已实现并通过验收。本变更是 Research 的第二个子能力：**财务审计员**，负责基于 data_engineering 提供的硬数据（财务指标）进行定量分析，结合 LLM 进行定性风险排查，输出结构化的财务健康评估（0–100 评分 + 5D 维度分析），供后续 Debate/Judge 使用。

**约束**：模块间调用必须通过被调用模块的 **Application 接口**，不得直接依赖对方领域模型或 Infrastructure。Research 依赖 data_engineering（财务指标）、llm_platform（LLM）；二者均已存在，但 data_engineering 当前的 `IFinancialDataRepository` **仅有 `save_all` 写入接口**，无任何读取/查询方法，也无对应的 Application 查询用例。

**已有资产**：
- 技术分析师已建立的模块骨架（domain/ports、application、infrastructure/adapters、agents/ 结构），可复用 `ILLMPort`、`prompt_loader`、以及 Domain 异常（`LLMOutputParseError`）等公共设施。
- 财务审计员的 System Prompt（5D 审计模型 + 评分协议）与 User Prompt 模板（静态快照 + 历史趋势）**已预先定义**（见 `system.md` 与 `user.md`）。

**相关方**：Coordinator（未来编排 Research）、Debate/Judge（消费 ResearchReport）；本变更仅实现财务审计员单元，不实现编排与报告聚合。

**测试约束**：Spec 中每个 Scenario 在交付时须有对应自动化测试；实现顺序灵活（可先实现再补测）。设计决策须考虑可测性（Port、DI、DTO），便于补测或按需 TDD。

## Goals / Non-Goals

**Goals:**

- 在 `src/modules/research/` 下新增财务审计员能力，复用已有模块骨架与公共设施（`ILLMPort`、`prompt_loader`、`LLMOutputParseError`）。
- 财务审计员通过 **Application 接口** 调用 data_engineering（获取财务指标）、llm_platform（LLM 调用），不直接依赖其 Domain/Infrastructure。
- 输入：股票代码（symbol）；系统自动获取该标的最近 N 期财务指标记录，构建为「静态快照 + 历史趋势」结构。输出：固定结构的 JSON（financial_score、signal、confidence、summary_reasoning、dimension_analyses、key_risks、risk_warning）。
- 与 LLM 的契约（已定义的 System/User Prompt）明确 5D 审计框架、证据驱动、不输出交易建议、冲突时降置信度；LLM 输出纯 JSON，由 Research 用 pydantic 解析并校验。
- 对外暴露独立 Application 入口（`FinancialAuditorService`），与技术分析师接口形态一致但各自独立。若提供 HTTP 接口，响应体 SHALL 由代码塞入 input、output、financial_indicators（与 technical_indicators 对称），便于调试与审计追溯。
- **可测性**：通过 Port 抽象与依赖注入，使 Application 层在无真实下游时可仅用 mock 验证行为；每个 Spec Scenario 可映射为可执行测试。

**Non-Goals:**

- 不实现 Coordinator、Debate、Judge；不实现 Research 的「并行五专家」编排与完整 ResearchReport 聚合。
- 不实现其余三专家（宏观情报员、估值建模师、催化剂侦探）。
- 不改变技术分析师的现有实现。
- 不实现财务数据的外部拉取/同步（data_engineering 已有 `SyncFinanceHistoryUseCase`），仅新增只读查询。

## Decisions

### 1. 财务数据的来源与 data_engineering 查询接口

- **选择**：
  - **数据来源**：Research 通过调用 data_engineering 的 **Application 接口** 获取持久化的财务指标数据（`StockFinance` 记录）。当前 data_engineering 无财务数据读取接口，本变更需在 data_engineering 中新增：
    1. `IFinancialDataRepository` 增加读方法 `get_by_third_code_recent(third_code: str, limit: int) -> List[StockFinance]`，按 `end_date` 降序返回最近 N 期记录。
    2. `pg_finance_repo` 实现该查询。
    3. 新增 Application 查询用例 `GetFinanceForTickerUseCase`（入参 ticker + limit，出参 `FinanceIndicatorDTO` 列表），遵循 `GetDailyBarsForTickerUseCase` 的已有模式：注入 Repository、查询、转 DTO 返回。
  - **DTO 设计**：`FinanceIndicatorDTO` 为 data_engineering Application 层对外暴露的 DTO，仅包含 Research 与其他消费方需要的财务指标字段（盈利、效率、偿债、现金流等），不暴露 `StockFinance` 的全部内部字段。
- **理由**：遵循「按标的+约束条件返回 DTO」的已有查询模式（对齐 `GetDailyBarsForTickerUseCase`）；Repository 读方法放在 Domain Port，实现在 Infrastructure，符合依赖倒置。

### 2. Domain 层三个抽象与跨模块调用

- **选择**：Research Domain 层包含三类与财务审计员相关的抽象：
  1. **获取财务指标数据**：Port（`IFinancialDataPort`），入参 ticker + limit，出参为 Research 内部定义的财务数据输入 DTO 列表（如 `FinanceRecordInput`）。由 Infrastructure Adapter 实现，内部调用 data_engineering 的 `GetFinanceForTickerUseCase`，将其 DTO 转为 Research 内部 DTO，不直接依赖 data_engineering 的 repository/domain。
  2. **构建财务快照**：Port（`IFinancialSnapshotBuilder`），入参为多期财务数据 DTO 列表，出参为与 User Prompt 模板一致的结构化快照（`FinancialSnapshotDTO`），包含静态快照（当期关键指标）与历史趋势序列（多季度时间序列），以及派生指标（quality_ratio = OCFPS/EPS、YoY 增速等）。**具体实现在 Infrastructure 层**，因涉及数据转换计算逻辑与潜在的第三方库依赖。
  3. **财务审计分析**：Port（`IFinancialAuditorAgentPort`），入参为财务快照 DTO 与上下文（symbol 等），出参为分析结果 DTO（`FinancialAuditAgentResult`，含解析后的 `FinancialAuditResultDTO` + 原始 LLM 输出 + user prompt）。实现层负责加载/填充 Prompt、调用 LLM、解析结果，Application 不直接依赖 LLMPort 或 prompt 加载实现。

  跨模块时，Research 的 Infrastructure Adapter 仅通过 data_engineering、llm_platform 的 **Application 接口** 获取数据或调用 LLM，不引用对方 domain 或 infrastructure。
- **理由**：与技术分析师保持一致的三层 Port 模式（数据获取 → 数据处理 → Agent 分析），Domain 只定义「做什么」的契约，实现（含数据转换/计算逻辑）在 Infrastructure；Application 编排仅依赖 Domain Port，符合依赖倒置与可测性。

### 3. Research 对 Coordinator 暴露的 Application 接口：按专家独立、不共用

- **选择**：延续技术分析师的模式。本变更对外仅暴露财务审计员专属入口 `FinancialAuditorService.run(symbol)`。Coordinator 编排时分别调用各专家的 Application 接口，而非调用统一的「Research 总入口」。**Application 与 HTTP 响应体**：返回结果 SHALL 包含解析后的审计 DTO 及 input、output、financial_indicators（代码塞入），与技术分析师的 input、output、technical_indicators 结构对称。
- **理由**：每个专家入参/出参与职责不同，独立接口便于契约清晰、单独编写测试与演进；响应体包含输入/输出/指标便于调试与审计追溯。

### 4. Prompt 资源复用已有模式

- **选择**：财务审计员的 System Prompt 与 User Prompt 模板存放在 `src/modules/research/agents/financial_auditor/prompts/`（`system.md` 与 `user.md`），与技术分析师的 `agents/technical_analyst/prompts/` 结构一致。运行时通过已有的 `prompt_loader` 加载；占位符在代码中用输入数据填充。**Prompt 内容已预先定义**，实现时直接从 `openspec/changes/research-financial-auditor/` 下的 `system.md` 与 `user.md` 拷贝至资源目录。
- **理由**：复用已有 prompt_loader 基础设施，避免重复建设；Prompt 已经过设计审查，直接使用。

### 5. LLM 调用与输出解析

- **选择**：复用已有 `ILLMPort`（llm_platform 的 `LLMService.generate`）传入 System Prompt 与填充后的 User Prompt；要求模型仅输出纯 JSON。**财务审计员的 JSON 格式与技术分析师不同**，解析逻辑内聚到 `agents/financial_auditor/output_parser.py`。Domain 层定义输出 DTO（`FinancialAuditResultDTO`），包含：
  - `financial_score`：int（0–100）
  - `signal`：Literal（STRONG_BULLISH / BULLISH / NEUTRAL / BEARISH / STRONG_BEARISH），与评分区间对应
  - `confidence`：float（0.0–1.0）
  - `summary_reasoning`：str（审计逻辑摘要，须引用输入指标读数）
  - `dimension_analyses`：list，每个维度含 `dimension`（维度名）、`score`（该维度评分）、`assessment`（简评）、`key_findings`（关键发现列表）
  - `key_risks`：list[str]（主要风险标记）
  - `risk_warning`：str（评估被证伪的关键条件）

  解析失败时记录日志（含 LLM 原始输出，可截断）并抛出 `LLMOutputParseError`。
- **理由**：各 Agent 返回的 JSON 结构不同，解析内聚到 Agent 可避免共享解析层膨胀；复用已有领域异常；单元测试可针对 output_parser 单独测。

### 6. 财务快照构建的具体逻辑

- **选择**：`IFinancialSnapshotBuilder` 的 Infrastructure 实现将多期 `FinanceRecordInput` 转为 `FinancialSnapshotDTO`，具体逻辑：
  1. 按 `end_date` 降序排列，Index 0 = 最新期。
  2. **静态快照**：取 Index 0 的记录，提取盈利（gross_margin、netprofit_margin、roe_waa、roic）、每股含金量（eps、profit_dedt 推算的扣非 EPS、ocfps、fcff_ps）、资产负债（current_ratio、quick_ratio、debt_to_assets、interestdebt、netdebt）、运营效率（invturn_days、arturn_days、assets_turn）。派生 `quality_ratio = ocfps / eps`（eps 为 0 时标记 N/A）。
  3. **历史趋势**：提取各期的 quarters 标签（由 `end_date` 推算季度，如 "2024Q3"）、各期 gross_margin/roic/fcff/invturn_days/arturn_days 组成时间序列。**YoY 增速**（revenue_growth_yoy、profit_growth_yoy）需要连续两期同比计算；如果 `StockFinance` 模型本身不含增速字段，则由构建器基于 `total_revenue_ps`（或等效字段）相邻同期计算，或标记为 N/A。
  4. 输出 `FinancialSnapshotDTO`，各字段与 User Prompt 模板占位符一一对应。
- **理由**：将数据转换与派生计算逻辑封装在 Infrastructure 实现中，通过 Domain Port 暴露，Application 不关心计算细节；便于测试（mock Port 返回固定快照）与后续调整计算逻辑。

### 7. 目录与分层结构

- **选择**：在 `src/modules/research/` 已有结构上扩展：
  - **domain/dtos.py**（或新建 `domain/financial_dtos.py`）：新增 `FinancialAuditResultDTO`、`DimensionAnalysisDTO`、`FinancialAuditAgentResult`。
  - **domain/ports/**：新增 `financial_data.py`（`IFinancialDataPort`）、`financial_snapshot_builder.py`（`IFinancialSnapshotBuilder`）、`financial_auditor_agent.py`（`IFinancialAuditorAgentPort`）。新增 `dto_financial_inputs.py`（`FinanceRecordInput`、`FinancialSnapshotDTO`）。
  - **application/financial_auditor_service.py**：编排「获取财务数据 → 构建快照 → 调用 Agent 分析 → 返回完整响应」。
  - **infrastructure/adapters/**：新增 `financial_data_adapter.py`（调用 data_engineering）、`financial_auditor_agent_adapter.py`（加载 Prompt + 调用 LLM + 解析）。新增 `infrastructure/financial_snapshot/`（快照构建实现）。
  - **agents/financial_auditor/**：含 `prompts/system.md`、`prompts/user.md`、`output_parser.py`。
  - **presentation/**：可新增财务审计员 REST 路由或留空。
- **理由**：与技术分析师的已有目录模式一致；各专家的 Port、Adapter、Agent 目录独立，互不干扰。

### 8. 实现顺序与测试

- **选择**：实现顺序**灵活**：可先实现再在交付前补全测试，也可在关键逻辑处先写测试再实现。Tasks 按实现块组织（data_engineering 查询接口 → Research Domain/Ports → 快照构建 → Agent + 解析 → Application 编排 → 完整测试），**最后统一做完整测试**，确保所有 Spec Scenario 有对应通过测试。
- **理由**：在保证可验证性的前提下减少步骤、加快执行；设计已考虑可测性（Port、DTO），便于补测。

## Risks / Trade-offs

| 风险 | 缓解 |
|------|------|
| LLM 返回非 JSON 或格式不稳定 | Prompt 明确要求「仅输出纯 JSON 字符串、无 Markdown 标记」；解析内聚于 `agents/financial_auditor/output_parser.py`，try/except + 日志，**解析失败时须将 LLM 原始输出写入日志（可截断）**；**测试覆盖「解析失败」Scenario**。 |
| data_engineering 尚无财务数据查询接口 | 本变更在 data_engineering 增加只读 Repository 方法 + Application 查询用例；遵循 `GetDailyBarsForTickerUseCase` 的已有模式，风险可控。 |
| `StockFinance` 模型不含 YoY 增速字段 | 快照构建器在 Infrastructure 层基于相邻同期记录计算 YoY；若数据不足则标记 N/A，不捏造数据。 |
| 5D 维度输出格式过于复杂导致 LLM 输出不稳定 | Prompt 中明确输出 JSON schema；output_parser 对 `dimension_analyses` 做宽松解析（允许部分维度缺失但记录警告）；测试覆盖各种边界情况。 |
| 财务审计员与技术分析师的公共设施耦合 | 二者共用 `ILLMPort`、`prompt_loader`、`LLMOutputParseError` 等公共设施，但各自的 Port、Adapter、Agent、DTO 完全独立；公共设施变更需考虑兼容性。 |

## Migration Plan

- **部署**：在已有 Research 模块上扩展，无存量数据迁移。data_engineering 仅新增只读查询（Repository 方法 + UseCase），不修改现有写入逻辑或数据库 schema（`stock_finance` 表已存在）。引入新依赖通过依赖注入在应用启动时装配。
- **回滚**：财务审计员为独立新增能力，回滚即停止调用该 Application 接口；data_engineering 新增的只读接口无副作用，可保留或移除。

## Open Questions

- `StockFinance` 中 `total_revenue_ps`（每股营业总收入）是否足以计算营收 YoY 增速，或是否需要原始营业收入总额？若字段不足，快照构建器可使用可用字段并在趋势中标记 N/A。
- 财务快照默认取最近几期（如 5 期季报）？还是允许调用方指定期数？初步决定默认 5 期，可通过参数覆盖。
- Presentation 层（REST 路由）是否在本变更中实现？暂定可选——核心交付为 Application 接口 + 测试通过。
