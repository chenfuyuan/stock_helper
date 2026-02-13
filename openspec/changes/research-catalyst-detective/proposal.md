# Proposal: Research 模块 — 催化剂侦探

## Why

Research 作为「事实工厂」需要五专家中最后一位 **催化剂侦探**，负责从**自下而上**的视角，搜索和识别可能触发标的股价显著变动的**具体催化事件**（公司重大动态、行业事件、市场情绪转变、业绩预期变化等），输出结构化的催化剂评估。催化剂侦探与宏观情报员形成互补：宏观情报员以**行业级**宏观环境为切入点（自上而下），而催化剂侦探聚焦**个股级**事件驱动因子（自下而上）。两者同为以 **软情报（Web 搜索）** 为主要数据源的角色，通过 llm_platform 已有的 `WebSearchService` 获取实时事件动态，结合 LLM 进行定性分析。核心信条为 **"寻找催化剂，捕捉变盘点 —— 股价的突破性变动往往由具体事件触发，及早识别催化因子是投资先机的关键。"** —— 观点必须基于 Web 搜索获取的可查证事件信息，杜绝 LLM 幻觉。

催化剂侦探是五专家的收官之作。本变更完成后，Research 模块的五专家体系（技术分析师、财务审计员、估值建模师、宏观情报员、催化剂侦探）将全部就绪，为后续 Coordinator 编排「并行五专家」和 Debate/Judge 流程奠定基础。

## What Changes

- **新增催化剂侦探角色**：以「资深事件驱动分析师 (Senior Event-Driven Analyst)」人设，采用 **四维催化剂扫描框架**（公司重大事件与动态 → 行业催化与竞争格局 → 市场情绪与机构动向 → 财报预期与业绩催化）对标的相关的催化事件进行系统性扫描与评估，不做最终交易决策。
- **输入契约**：接受股票代码（symbol）；系统自动：
  1. 从 data_engineering 获取该标的的**股票基础信息**（名称、行业、代码）—— 通过已有的 `GetStockBasicInfoUseCase`。
  2. 基于**公司名称与行业上下文**，通过 llm_platform 的 `WebSearchService` 执行**多主题催化剂搜索**（公司动态、行业事件、机构动向、业绩预期等），获取实时催化事件情报。
  搜索查询 SHALL 由代码根据**公司名称**和行业上下文动态生成（如"XX公司 重大事件 2026""XX公司 并购重组 管理层变动""XX行业 竞争格局 技术突破"等）。**与宏观情报员的核心差异**：搜索查询包含**公司名称**以聚焦个股级催化事件，而非仅行业级宏观动态。搜索结果在 Research 内部经过结构化处理后，作为硬证据填入 User Prompt 模板。
- **输出契约**：固定 JSON 结构，包含：`catalyst_assessment`（Positive (正面催化) / Neutral (中性) / Negative (负面催化)）、`confidence_score`（0.0–1.0）、`catalyst_summary`（催化剂综合评估摘要，须引用搜索证据）、`dimension_analyses`（四维各自的评估、评分与关键发现）、`positive_catalysts`（正面催化事件列表，每项含事件描述 event、预期影响 expected_impact、时间线 timeframe、触发概率 probability）、`negative_catalysts`（负面催化事件/风险列表，每项含事件描述 event、预期影响 expected_impact、时间线 timeframe、触发概率 probability）、`information_sources`（引用的信息来源 URL 列表，用于溯源审计）。
- **绝对约束**：证据驱动（观点必须引用 Web 搜索获取的具体事件信息作为证据，并标注来源 URL）；不输出「建议买入/卖出」等交易指令；LLM 不得捏造未搜索到的催化事件或公司动态；当搜索结果不足或信息过时时，须明确声明"信息有限"并降低置信度。
- **集成方式**：催化剂侦探作为 Research 内一个独立分析单元，依赖 data_engineering（股票基础信息）、llm_platform（Web 搜索 + LLM 调用）的 **Application 接口**。本变更仅暴露催化剂侦探专属入口（如 `CatalystDetectiveService`），Coordinator 直接调用该接口。
- **Prompt 归属与存放**：System Prompt 与 User Prompt 模板**内聚在该专家中**，存放在 `agents/catalyst_detective/prompts/`（`system.md` 与 `user.md`），运行时加载，模板占位符在代码中用搜索结果与股票基础信息填充。Prompt 内容已预先定义（见本变更目录下的 `system.md` 与 `user.md`）。User Prompt 使用 `{...}` 单花括号占位符（Python `str.format()` 风格），共 9 个占位符：`stock_name`、`third_code`、`current_date`、`industry`、`company_events_context`、`industry_catalyst_context`、`market_sentiment_context`、`earnings_context`、`all_source_urls`。
- **无上游前置依赖变更**：与宏观情报员一致，本变更**不需修改 data_engineering 或 llm_platform 的现有实现**。`GetStockBasicInfoUseCase`、`WebSearchService`（及其 `LLMPlatformContainer.web_search_service()` 工厂方法）、`LLMService` 均已就绪。宏观情报员变更中已完成的 `LLMPlatformContainer.web_search_service()` 扩展可直接复用。
- **实现与验证方式**：Spec 中每个 Scenario 在变更完成时须有对应自动化测试；实现顺序灵活，交付以**完整测试通过**为完成标准。

## Capabilities

### New Capabilities

- **`research-catalyst-detective`**：催化剂侦探能力。定义输入（股票代码 → 系统获取股票基础信息 + 执行多主题催化剂 Web 搜索）、输出（CatalystDetectiveResult JSON 结构）、四维催化剂扫描框架（公司重大事件与动态 / 行业催化与竞争格局 / 市场情绪与机构动向 / 财报预期与业绩催化）、与 LLM 的 Prompt 契约（证据驱动/来源标注/输出纯 JSON），以及搜索结果的结构化处理规约。每个需求下的 Scenario 在交付时须有对应自动化测试。

### Modified Capabilities

- （无。宏观情报员、技术分析师、财务审计员与估值建模师的能力 spec 不受影响；五者为独立专家，各自有独立 Application 接口。）

## Impact

- **代码**：在 `src/modules/research/` 下新增催化剂侦探相关 Domain（输入/输出 DTO）、Application 服务（编排股票信息获取 + Web 搜索 + 催化剂上下文构建 + LLM 调用 + 解析）、Domain Port（`ICatalystDataPort`、`ICatalystContextBuilder`、`ICatalystDetectiveAgentPort`）及 Infrastructure 适配。新增 `agents/catalyst_detective/` 目录含 Prompt 资源与输出解析器。**复用宏观情报员已建立的三层 Port 模式**（数据获取 → 数据处理 → Agent 分析）与已有公共设施（`ILLMPort`、`prompt_loader` 加载模式、`LLMOutputParseError`）。
- **依赖**：Research 依赖 data_engineering（股票基础信息，通过已有 `GetStockBasicInfoUseCase`）、llm_platform（Web 搜索通过已有 `WebSearchService` + LLM 调用通过已有 `LLMService`）；不依赖 Coordinator/Debate/Judge。**无需修改 data_engineering 或 llm_platform 的现有实现**。`LLMPlatformContainer.web_search_service()` 已在宏观情报员变更中就绪。
- **API/系统**：催化剂侦探产出为 ResearchReport 的一个片段。Research 对 Coordinator 按专家暴露独立接口（本变更仅催化剂侦探一个接口）。若提供 HTTP 接口，响应体 SHALL 与其他四专家一致：包含 input、output、catalyst_indicators（代码塞入的催化剂上下文，便于调试与审计追溯）。
- **测试与可验证性**：Spec 中所有 Scenario 在交付时须有对应自动化测试；交付完成以「完整测试通过 + 无跨模块直接依赖」为验收条件。
- **非目标**：本变更不实现 Research 的「并行五专家」编排、不实现 Debate/Judge；不改变现有四专家的实现。
