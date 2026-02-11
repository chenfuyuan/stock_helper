# Design: Research 模块 — 技术分析师

## Context

Research 是愿景中的「事实工厂」Bounded Context，目前代码库中尚未存在（`src/modules/research/` 待建）。本变更是 Research 的首个子能力：**技术分析师**，负责将预计算的技术指标与形态整合为证据驱动的技术面观点（JSON），供后续 Debate/Judge 使用。

**约束**：模块间调用必须通过被调用模块的 **Application 接口**，不得直接依赖对方领域模型或 Infrastructure。Research 依赖 data_engineering（行情/日线等）、llm_platform（LLM）；二者均已存在，但 data_engineering 当前以同步类命令（Sync*）和单一查询（GetStockBasicInfo）为主，尚无「按标的+日期返回日线或预计算技术指标」的 Application 接口。

**相关方**：Coordinator（未来编排 Research）、Debate/Judge（消费 ResearchReport）；本变更仅实现技术分析师单元，不实现编排与报告聚合。

**测试约束**：Spec 中每个 Scenario 在交付时须有对应自动化测试；实现顺序灵活（可先实现再补测）。设计决策须考虑可测性（Port、DI、DTO），便于补测或按需 TDD。

## Goals / Non-Goals

**Goals:**

- 在 `src/modules/research/` 下建立符合 DDD 四层的技术分析师能力。
- 技术分析师通过 **Application 接口** 调用 data_engineering、llm_platform，不直接依赖其 Domain/Infrastructure。
- 输入：目标资产信息 + 预计算技术指标与形态（趋势/均线、动量、量能、形态与关键价位）；输出：固定结构的 JSON（signal、confidence、summary_reasoning、key_technical_levels、risk_warning）。
- 与 LLM 的契约（System Prompt + User Prompt 模板）明确证据驱动、不输出交易建议、冲突时降置信度；LLM 输出纯 JSON，由 Research 用 pydantic 解析并校验。
- 为后续「五专家并行」与 ResearchReport 聚合预留接口形态（例如技术分析结果为报告的一个片段）。
- **可测性**：通过 Port 抽象与依赖注入，使 Application 层在无真实下游时可仅用 mock 验证行为；每个 Spec Scenario 可映射为可执行测试。

**Non-Goals:**

- 不实现 Coordinator、Debate、Judge；不实现 Research 的「并行五专家」编排与完整 ResearchReport 聚合。
- 不在本变更内把「预计算指标」能力下沉到 data_engineering 或其它模块；指标计算归属已定：Research Domain Port + Research Infrastructure 实现（见决策 1、2）。

## Decisions

### 1. 技术指标与形态的数据来源与计算归属

- **选择**：
  - **数据来源**：Research 通过调用 data_engineering 的 **Application 接口** 获取原始日线（或 K 线）数据。若 data_engineering 尚无「按标的+日期区间返回日线」的 Application 接口，则本变更在 data_engineering 中新增只读查询用例（如 `GetDailyBarsForTicker`），返回 DTO。
  - **指标计算**：**在 Domain 层定义抽象 Port**（如 `IIndicatorCalculator` 或 `ITechnicalIndicatorCalculator`），入参为日线数据（DTO），出参为与 spec 输入契约一致的技术指标快照（如 `TechnicalIndicatorsSnapshot`）。**具体实现在 Infrastructure 层**，实现可依赖第三方库（如 ta-lib、pandas、numpy 等）进行 RSI、MA、MACD、KDJ、ADX、OBV 及形态/支撑阻力计算；Application 仅依赖该 Port，不直接依赖 Infrastructure 或第三方库。
- **理由**：技术指标计算**并非纯函数**，可能依赖第三方库或外部实现细节，故不宜作为「无 I/O 的 Domain Service」放在 Domain 实现里；将契约放在 Domain（Port）、实现放在 Infrastructure 符合依赖倒置，且便于测试时 mock、后续更换或升级计算库而不影响 Application 与 Domain。

### 2. Domain 层三个抽象与跨模块调用

- **选择**：Research Domain 层包含三类与技术分析师相关的抽象：
  1. **获取日线数据**：Port（如 `IMarketQuotePort`），由 Infrastructure Adapter 实现，内部调用 data_engineering 的 **Application 接口** 获取日线，不直接依赖其 repository/domain。
  2. **计算技术指标**：Port（如 `IIndicatorCalculator`），入参日线 DTO、出参指标快照；**具体实现在 Infrastructure**，实现可依赖第三方库（ta-lib、pandas 等），Application 不直接调用 Infrastructure 或第三方库。
  3. **技术分析**：Port（如「技术分析 Agent」Port），入参指标快照与上下文，出参分析结果 DTO；实现层负责加载/填充 Prompt、调用 LLM、解析结果，Application 不直接依赖 LLMPort 或 prompt 加载实现。

  跨模块时，Research 的 Infrastructure Adapter 仅通过 data_engineering、llm_platform 的 **Application 接口** 获取数据或调用 LLM，不引用对方 domain 或 infrastructure。
- **理由**：Domain 只定义「做什么」的契约，实现（含第三方库依赖）在 Infrastructure；Application 编排仅依赖 Domain Port，符合依赖倒置与可测性。

### 3. Research 对 Coordinator 暴露的 Application 接口：按专家独立、不共用

- **选择**：Research 提供给 Coordinator 的接口是**按专家拆分的独立 Application 接口**，五专家**不共用**同一个入口。本变更只实现技术分析师，故对外仅暴露技术分析师专属入口，例如 `TechnicalAnalystService.run(ticker, analysis_date)` 或 `RunTechnicalAnalysisUseCase.execute(input_dto)`。Coordinator 编排时分别调用各专家的 Application 接口，而非调用一个统一的「Research 总入口」。
- **理由**：每个专家入参/出参与职责不同，独立接口便于契约清晰、**单独为每个专家编写测试**与演进。

### 4. Prompt 内聚于对应 Agent、存放于代码外

- **选择**：每个专家的 System Prompt 与 User Prompt 模板**内聚在该专家（agent）的上下文中**，但**不得将 prompt 正文硬编码在代码里**。Prompt 存放在**代码库内的资源目录**（如 `src/modules/research/agents/technical_analyst/prompts/` 下的 `.md` 或 `.txt` 文件），或项目约定的资源路径，由该专家的 Application 或 Infrastructure 在**运行时加载**；占位符在代码中填充。
- **理由**：Prompt 易迭代、可交给非开发角色维护；**测试时可通过替换资源路径或注入 Prompt 加载 Port 的 mock 提供固定模板**，便于可重复测试。

### 5. LLM 调用与输出解析

- **选择**：使用 llm_platform 的 **Application 接口**（现有 `LLMService.generate(system_message=..., prompt=...)`）传入**从资源加载的** System Prompt 与填充后的 User Prompt；要求模型仅输出纯 JSON。**每个 Agent 的 LLM 输出 JSON 格式可能不同，解析逻辑内聚到该 Agent**（如技术分析师为 `agents/technical_analyst/output_parser.py`），由该 Agent Port 的 Infrastructure 实现在拿到 LLM 字符串后调用；Domain 保留输出 DTO 与领域异常（如 `TechnicalAnalysisResultDTO`、`LLMOutputParseError`），解析实现与格式约定归属具体 Agent，便于后续各专家独立演进。若解析失败则记录日志并抛出领域友好异常；**解析失败时须将 LLM 原始输出写入日志（可截断），便于排查**。
- **理由**：各 Agent 返回的 JSON 结构不同，解析内聚到 Agent 可避免 Domain 或共享解析层随专家增多而膨胀；单元测试可针对各 Agent 的 output_parser 单独测；失败时打印原始输出便于调试。

### 6. 目录与分层结构

- **选择**：`src/modules/research/` 下按四层组织：
  - **application/**：按专家拆分，编排「收集数据 → 计算技术指标（调 Port）→ 分析（调 Port）→ 输出报告」；不直接调用 Infrastructure 或第三方库。
  - **domain/**：值对象、输出/输入 DTO、**ports 定义**（如 `IMarketQuotePort`、`IIndicatorCalculator`、技术分析 Agent 的 Port）、领域异常（如 `LLMOutputParseError`）；**不包含**各 Agent 的 LLM 输出解析实现或指标计算/LLM 调用的具体实现。
  - **infrastructure/**：**指标计算 Port 的具体实现**（可依赖第三方库）、调用 data_engineering/llm_platform 的 Adapter、Prompt 资源加载与填充；技术分析 Agent Port 的实现（内部用 prompt 加载 + LLM 调用 + 调用该 Agent 的 output_parser）。
  - **agents/<agent_name>/**：每个专家内聚 Prompt 资源（如 `prompts/`）与**该专家专属的 LLM 输出解析**（如 `output_parser.py`），各 Agent 的 JSON 格式与解析逻辑互不干扰。
  - **presentation/**：本变更可留空或占位。
- **理由**：与 vision-and-modules §4 一致；指标计算因可能依赖第三方库而落在 Infrastructure，通过 Domain Port 暴露；Application 仅依赖 Port，便于测试与替换实现。

### 7. 实现顺序与测试

- **选择**：实现顺序**灵活**：可先实现再在交付前补全测试，也可在关键逻辑处先写测试再实现。Tasks 按实现块组织（如日线接口、Research 骨架、解析、Adapter、Prompt、编排），**最后统一做完整测试**，确保所有 Spec Scenario 有对应通过测试。
- **理由**：在保证可验证性的前提下减少步骤、加快执行；设计已考虑可测性（Port、DTO），便于补测。

## Risks / Trade-offs

| 风险 | 缓解 |
|------|------|
| LLM 返回非 JSON 或格式不稳定 | 明确 Prompt 要求「仅输出合法 JSON、无 Markdown」；解析内聚于各 Agent（如 output_parser.py），try/except + 日志，**解析失败时须将 LLM 原始输出写入日志（可截断）**；**测试覆盖「解析失败」Scenario**；必要时重试或返回 NEUTRAL + 低置信度。 |
| data_engineering 尚无日线查询 Application 接口 | 本变更在 data_engineering 增加只读 UseCase + DTO；tasks 中**先写该接口的测试再实现**。 |
| 指标计算依赖第三方库或实现复杂度增长 | 指标计算为 **Domain Port + Infrastructure 实现**，实现可依赖 ta-lib 等第三方库；替换或升级库时仅改 Infrastructure，Domain/Application 不变；为 Port 契约与输出结构写测试，便于 mock 与重构。 |
| 技术分析师与其余四专家接口不一致 | Research 对 Coordinator 按专家暴露独立 Application 接口；各专家复用「DTO + Application 服务 + 资源化 Prompt」模式；**每专家独立测试**。 |

## Migration Plan

- **部署**：新模块，无存量数据迁移。引入新依赖通过依赖注入在应用启动时装配。
- **回滚**：若仅启用 Research 技术分析师，可通过配置或编排层关闭该能力；无数据库 schema 变更，回滚即停止调用。

## Open Questions

- 形态识别（K 线形态、支撑/阻力）本迭代做到何种粒度由 specs/tasks 细化。
- data_engineering 日线查询接口的命名与返回 DTO 字段需与 data_engineering 现有模型对齐，可在 tasks 中与 data_engineering 变更一起定稿。
