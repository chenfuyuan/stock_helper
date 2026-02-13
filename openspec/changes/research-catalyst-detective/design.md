# Design: Research 模块 — 催化剂侦探

## Context

Research 是愿景中的「事实工厂」Bounded Context，代码库中已存在（`src/modules/research/`），其中**技术分析师**、**财务审计员**、**估值建模师**与**宏观情报员**能力已实现并通过验收。本变更是 Research 的第五个也是**最后一个**子能力：**催化剂侦探**，负责从自下而上的视角，通过 Web 搜索识别可能触发标的股价显著变动的**具体催化事件**（公司重大动态、行业事件、市场情绪变化、业绩预期变化），结合 LLM 进行定性分析，输出结构化的催化剂评估（Positive / Neutral / Negative + 四维分析 + 正面/负面催化事件清单），供后续 Debate/Judge 使用。

**与宏观情报员的核心差异**：
- 宏观情报员以**行业级宏观环境**为切入点（自上而下），搜索查询仅包含行业关键词，聚焦货币政策/产业政策/宏观经济/行业景气。
- 催化剂侦探聚焦**个股级事件驱动因子**（自下而上），搜索查询**包含公司名称**，聚焦公司事件/行业催化/机构动向/业绩预期。
- 宏观情报员输出 `key_opportunities`/`key_risks`（简单字符串列表）；催化剂侦探输出 `positive_catalysts`/`negative_catalysts`（**结构化事件列表**，含 event、expected_impact、timeframe、probability）。
- 两者同为 Web 搜索驱动，共享相同的上游依赖（data_engineering + llm_platform），复用已有的 `WebSearchService` 和 `LLMPlatformContainer.web_search_service()` 工厂方法。

**约束**：模块间调用必须通过被调用模块的 **Application 接口**，不得直接依赖对方领域模型或 Infrastructure。Research 依赖 data_engineering（股票信息）、llm_platform（Web 搜索 + LLM）。

**已有资产**：
- 四专家已建立的模块骨架（domain/ports、application、infrastructure/adapters、agents/ 结构），可复用 `ILLMPort`、`prompt_loader` 加载模式、`LLMOutputParseError` 等公共设施。
- 宏观情报员已建立的**三层 Port 模式**（数据获取 → 上下文构建 → Agent 分析），可作为催化剂侦探的直接参照。
- llm_platform 已有 `WebSearchService`（Application 接口）、`WebSearchRequest`/`WebSearchResponse` DTO（含 `to_prompt_context()` 方法）、`BochaWebSearchAdapter` 实现。`LLMPlatformContainer.web_search_service()` 工厂方法已在宏观情报员变更中就绪。
- data_engineering 已有 `GetStockBasicInfoUseCase` → `StockBasicInfoDTO(info: StockInfo, daily: StockDaily)`。
- 催化剂侦探的 System Prompt 与 User Prompt 模板**已预先定义**（见 `system.md` 与 `user.md`）。

**相关方**：Coordinator（未来编排 Research）、Debate/Judge（消费 ResearchReport）；本变更仅实现催化剂侦探单元，不实现编排与报告聚合。

**测试约束**：Spec 中每个 Scenario 在交付时须有对应自动化测试；实现顺序灵活（可先实现再补测）。设计决策须考虑可测性（Port、DI、DTO），便于补测或按需 TDD。

## Goals / Non-Goals

**Goals:**

- 在 `src/modules/research/` 下新增催化剂侦探能力，复用已有模块骨架与公共设施（`ILLMPort`、prompt 加载模式、`LLMOutputParseError`）、宏观情报员建立的三层 Port 模式。
- 催化剂侦探通过 **Application 接口** 调用 data_engineering（获取股票基础信息）、llm_platform（Web 搜索 + LLM 调用），不直接依赖其 Domain/Infrastructure。
- 输入：股票代码（symbol）；系统自动获取股票基础信息（名称/行业/代码），并基于**公司名称**与行业上下文执行多主题 Web 搜索。搜索结果在 Research 内部经过结构化处理后填入 User Prompt。输出：固定结构 JSON（catalyst_assessment、confidence_score、catalyst_summary、dimension_analyses、positive_catalysts、negative_catalysts、information_sources）。
- 对外暴露独立 Application 入口（`CatalystDetectiveService`），与其他四专家接口形态一致但各自独立。HTTP 响应体 SHALL 包含 input、output、catalyst_indicators（代码塞入的催化剂上下文快照），与 technical_indicators / financial_indicators / valuation_indicators / macro_indicators 结构对称。
- **可测性**：通过 Port 抽象与依赖注入，使 Application 层在无真实下游时可仅用 mock 验证行为；每个 Spec Scenario 可映射为可执行测试。

**Non-Goals:**

- 不实现 Coordinator、Debate、Judge；不实现 Research 的「并行五专家」编排与完整 ResearchReport 聚合。
- 不改变技术分析师、财务审计员、估值建模师与宏观情报员的现有实现。
- 不实现自定义搜索引擎或爬虫（使用 llm_platform 已有的 WebSearchService）。
- 不修改 data_engineering 或 llm_platform 的现有实现。

## Decisions

### 1. 数据来源：复用宏观情报员的上游依赖，零新增接口

- **选择**：催化剂侦探所需的上游接口与宏观情报员完全一致：

  | 数据类别 | 上游模块 | 接口 | 状态 |
  |----------|---------|------|------|
  | 股票基础信息（名称、行业、代码） | data_engineering | `GetStockBasicInfoUseCase` → `StockBasicInfoDTO` | **已有** |
  | 催化事件搜索结果 | llm_platform | `WebSearchService.search(WebSearchRequest)` → `WebSearchResponse` | **已有** |
  | LLM 分析 | llm_platform | `LLMService.generate(prompt, system_message)` → `str` | **已有**（通过 `ILLMPort`） |

  **无需新增上游接口**。`LLMPlatformContainer.web_search_service()` 已在宏观情报员变更中就绪，可直接复用。

- **理由**：催化剂侦探与宏观情报员的上游依赖完全重叠，差异仅在于搜索查询内容（个股级 vs 行业级）和 LLM Prompt（催化事件 vs 宏观环境），不影响上游接口。

### 2. Domain 层三个抽象：延续三层 Port 模式

- **选择**：Research Domain 层新增三个催化剂侦探相关的抽象，延续已有的三层 Port 模式（数据获取 → 数据处理 → Agent 分析）：

  1. **获取催化剂所需数据**：Port（`ICatalystDataPort`），包含两个方法：
     - `get_stock_overview(symbol) -> Optional[CatalystStockOverview]`：获取股票基础信息（stock_name、industry、third_code）。Adapter 内部调用 `GetStockBasicInfoUseCase`，提取所需字段转为 Research 内部 DTO。返回 None 表示标的不存在。
     - `search_catalyst_context(stock_name, industry) -> List[CatalystSearchResult]`：基于**公司名称**与行业上下文执行多主题催化剂搜索。Adapter 内部调用 llm_platform 的 `WebSearchService`，按四个维度分别构建搜索查询，汇总返回。每个 `CatalystSearchResult` 包含维度标识（dimension_topic）与该维度下的搜索结果条目列表。

  2. **构建催化剂上下文**：Port（`ICatalystContextBuilder`），入参为 `CatalystStockOverview` + `List[CatalystSearchResult]`，出参为 `CatalystContextDTO`（与 User Prompt 模板占位符一一对应）。**处理逻辑在 Infrastructure 层实现**（见 Decision 4）。

  3. **催化剂分析**：Port（`ICatalystDetectiveAgentPort`），入参为 `CatalystContextDTO`，出参为 `CatalystDetectiveAgentResult`（含解析后的 `CatalystDetectiveResultDTO` + 原始 LLM 输出 + user prompt）。实现层负责加载/填充 Prompt、调用 LLM、解析结果。

  跨模块时，Research 的 Infrastructure Adapter 仅通过 data_engineering 的 **Application 接口**（`GetStockBasicInfoUseCase`）和 llm_platform 的 **Application 接口**（`WebSearchService`、`LLMService`）获取数据或调用能力，不引用对方 domain 或 infrastructure。

- **理由**：与宏观情报员保持完全一致的三层 Port 模式，确保架构一致性。`ICatalystDataPort` 的 `search_catalyst_context` 方法入参为 `(stock_name, industry)` 而非宏观情报员的 `(industry, stock_name)`，反映催化剂侦探**以公司名称为主、行业为辅**的搜索策略。

### 3. CatalystStockOverview 复用 MacroStockOverview 的字段集，但独立定义

- **选择**：为催化剂侦探新增专属输入 DTO `CatalystStockOverview`，包含 `stock_name`、`industry`、`third_code` 三个字段。字段集与 `MacroStockOverview` 完全相同，但为独立类定义。
- **备选**：复用 `MacroStockOverview`，在催化剂侦探中 import 使用。
- **理由**：各专家的输入 DTO 独立演进，互不影响；催化剂侦探未来可能需要额外字段（如市值区间、上市时间等用于调整搜索策略），独立 DTO 语义清晰，避免耦合。与宏观情报员 Decision 9 的决策一致。

### 4. 催化剂上下文构建：按维度归类搜索结果，填充公司名称

- **选择**：`ICatalystContextBuilder` 的 Infrastructure 实现将股票概览与搜索结果转为 `CatalystContextDTO`，具体处理逻辑：

  1. **按维度归类**：将 `List[CatalystSearchResult]`（每个已标注 dimension_topic）按四个维度归类，每个维度的搜索结果转为格式化的文本段落（标题 + 来源 + 日期 + 摘要/内容）。
  2. **来源 URL 收集**：从所有搜索结果中提取去重的 URL 列表，作为 `all_source_urls`。
  3. **空结果处理**：若某维度搜索返回 0 条结果，该维度的上下文标记为"该维度暂无搜索结果，信息有限"；LLM Prompt 已约定遇到信息不足时须声明并降低置信度。
  4. **输出 `CatalystContextDTO`**：各字段与 User Prompt 模板占位符一一对应，包含：`stock_name`、`third_code`、`industry`（均从 `CatalystStockOverview` 透传）、`current_date`（构建时由代码生成，格式如"2026-02-13"）、`company_events_context`（公司事件搜索摘要）、`industry_catalyst_context`（行业催化搜索摘要）、`market_sentiment_context`（市场情绪搜索摘要）、`earnings_context`（业绩预期搜索摘要）、`all_source_urls`（来源 URL 列表字符串）。共 9 个字段，与 `user.md` 模板中的 9 个 `{...}` 占位符一一对应。

- **理由**：与宏观情报员 Decision 4 完全对称。ContextBuilder 的处理逻辑相同（按维度归类 + URL 收集 + 空结果标记），差异仅在于维度名称和搜索内容。

### 5. 搜索策略：四维度 × 公司名称查询 × 时效过滤

- **选择**：`CatalystDataAdapter` 的 `search_catalyst_context` 方法按四个维度构建搜索查询并执行：

  | 维度 | 查询模板（示例） | freshness |
  |------|----------------|-----------|
  | 公司重大事件 | `"{stock_name} 重大事件 并购重组 管理层变动 战略合作 {year}年"` | `oneMonth` |
  | 行业催化与竞争 | `"{stock_name} {industry} 竞争格局 技术突破 政策催化 {year}年"` | `oneMonth` |
  | 市场情绪与机构 | `"{stock_name} 机构评级 分析师 调研 资金流向 {year}年"` | `oneMonth` |
  | 财报预期与业绩 | `"{stock_name} 业绩预告 财报 盈利预测 订单合同 {year}年"` | `oneMonth` |

  每个查询使用 `count=8`（每维度最多 8 条结果），启用 AI 摘要（`summary=True`）。四次搜索**顺序执行**。

  **与宏观情报员的核心差异**：所有查询**以 `stock_name` 开头**，确保搜索结果聚焦于该个股的催化事件。宏观情报员的查询仅包含行业和宏观关键词，不含公司名称。

- **备选**：并发执行四次搜索（`asyncio.gather`）。
- **理由**：与宏观情报员一致，顺序执行简单可靠，四次搜索的总延迟在可接受范围内（约 2-4 秒）；若未来性能成为瓶颈，可轻松切换为 `asyncio.gather` 并发。

### 6. Web 搜索错误的优雅降级

- **选择**：与宏观情报员 Decision 6 完全一致。`CatalystDataAdapter` 中的每个维度搜索独立 try/except：若某维度搜索失败，记录警告日志，该维度返回空结果（`CatalystSearchResult(dimension_topic=..., items=[])`），不中断整体分析流程。全部搜索失败时，`CatalystDetectiveService` 抛出 `BadRequestException`。
- **理由**：催化剂分析是定性的，部分信息缺失仍可给出有限但诚实的判断；全部失败则无法提供有价值的分析。

### 7. Prompt 资源复用已有模式

- **选择**：催化剂侦探的 System Prompt 与 User Prompt 模板存放在 `src/modules/research/infrastructure/agents/catalyst_detective/prompts/`（`system.md` 与 `user.md`），运行时通过与已有专家相同的加载模式读取。在 `prompt_loader.py` 中新增催化剂侦探的加载与填充函数。User Prompt 使用 `{...}` 单花括号占位符（Python `str.format()` 风格），与已有四专家一致。**Prompt 内容已预先定义**，实现时直接从 `openspec/changes/research-catalyst-detective/` 下的 `system.md` 与 `user.md` 拷贝至资源目录。
- **理由**：复用已有 prompt 加载基础设施模式，避免重复建设；占位符风格统一。

### 8. LLM 调用与输出解析

- **选择**：复用已有 `ILLMPort`（llm_platform 的 `LLMService.generate`）传入 System Prompt 与填充后的 User Prompt；要求模型仅输出纯 JSON。**催化剂侦探的 JSON 结构与其他专家不同**，解析逻辑内聚到 `agents/catalyst_detective/output_parser.py`。Domain 层定义输出 DTO，包含：
  - `CatalystDetectiveResultDTO`：
    - `catalyst_assessment`：Literal（"Positive (正面催化)" / "Neutral (中性)" / "Negative (负面催化)"）
    - `confidence_score`：float（0.0–1.0），基于证据充分性与一致性
    - `catalyst_summary`：str（催化剂综合评估，须引用搜索证据）
    - `dimension_analyses`：list[CatalystDimensionAnalysis]，每个维度含 `dimension`（维度名）、`assessment`（评估）、`score`（0–100）、`key_findings`（关键发现列表）
    - `positive_catalysts`：list[CatalystEvent]（正面催化事件列表）
    - `negative_catalysts`：list[CatalystEvent]（负面催化事件/风险列表）
    - `information_sources`：list[str]（引用的信息来源 URL 列表）
  - `CatalystEvent`（催化事件值对象）：
    - `event`：str（事件描述）
    - `expected_impact`：str（预期对股价/基本面的影响）
    - `timeframe`：str（时间线：近期/中期/远期）
    - `probability`：str（触发概率：高/中/低）
  - `CatalystDimensionAnalysis`：与 `MacroDimensionAnalysis` 结构相同（dimension、assessment、score、key_findings），独立定义。

  解析失败时记录日志（含 LLM 原始输出，可截断）并抛出 `LLMOutputParseError`。输出解析器复用 `_strip_thinking_tags`（剥离 `<think>` 标签）和 markdown 代码块剥离逻辑。

- **理由**：各 Agent 返回的 JSON 结构不同，解析内聚到 Agent 可避免共享解析层膨胀；`CatalystEvent` 作为结构化值对象，比简单字符串列表更能表达催化事件的时间性和概率性，这是催化剂侦探区别于宏观情报员的核心差异。

### 9. Research 对 Coordinator 暴露的 Application 接口：按专家独立

- **选择**：延续已有四专家的模式。本变更对外仅暴露催化剂侦探专属入口 `CatalystDetectiveService.run(symbol)`。HTTP 响应体包含解析后的催化剂分析 DTO 及 input、output、catalyst_indicators（代码塞入），与其他四专家对称。
- **理由**：每个专家入参/出参与职责不同，独立接口便于契约清晰、单独编写测试与演进。

### 10. 目录与分层结构

- **选择**：在 `src/modules/research/` 已有结构上扩展：
  - **domain/dtos/catalyst_inputs.py**：新增 `CatalystStockOverview`（stock_name、industry、third_code）、`CatalystSearchResultItem`（title、url、snippet、summary: Optional、site_name: Optional、published_date: Optional）、`CatalystSearchResult`（dimension_topic: str、items: List[CatalystSearchResultItem]）。
  - **domain/dtos/catalyst_context.py**：新增 `CatalystContextDTO`（9 个字段与 user.md 占位符一一对应：stock_name、third_code、industry、current_date、company_events_context、industry_catalyst_context、market_sentiment_context、earnings_context、all_source_urls）。
  - **domain/dtos/catalyst_dtos.py**：新增 `CatalystEvent`（event、expected_impact、timeframe、probability）、`CatalystDimensionAnalysis`（dimension、assessment、score: int 0-100、key_findings: list[str]）、`CatalystDetectiveResultDTO`（catalyst_assessment: Literal 三值、confidence_score: float 0-1、catalyst_summary、dimension_analyses: list[CatalystDimensionAnalysis] 4 项、positive_catalysts: list[CatalystEvent]、negative_catalysts: list[CatalystEvent]、information_sources: list[str]）、`CatalystDetectiveAgentResult`（result + raw_llm_output + user_prompt）。
  - **domain/ports/catalyst_data.py**：`ICatalystDataPort`（2 个方法：get_stock_overview + search_catalyst_context）。
  - **domain/ports/catalyst_context_builder.py**：`ICatalystContextBuilder`。
  - **domain/ports/catalyst_detective_agent.py**：`ICatalystDetectiveAgentPort`。
  - **application/catalyst_detective_service.py**：编排「校验 → 获取股票概览（校验非空）→ 执行催化剂搜索 → 校验搜索结果非全空 → 构建催化剂上下文 → 调用 Agent → 返回完整响应」。
  - **infrastructure/adapters/catalyst_data_adapter.py**：实现 `ICatalystDataPort`（内部调用 data_engineering `GetStockBasicInfoUseCase` + llm_platform `WebSearchService`）。
  - **infrastructure/adapters/catalyst_detective_agent_adapter.py**：实现 `ICatalystDetectiveAgentPort`（加载 Prompt + 调用 LLM + 解析）。
  - **infrastructure/catalyst_context/context_builder.py**：实现 `ICatalystContextBuilder`（结构化搜索结果为维度对齐上下文）。
  - **infrastructure/agents/catalyst_detective/prompts/**：`system.md`、`user.md`。
  - **infrastructure/agents/catalyst_detective/output_parser.py**：解析 LLM JSON 输出。
  - **presentation/rest/catalyst_detective_routes.py**：催化剂侦探 REST 路由，与已有四专家路由同级同模式。
- **理由**：与已有四专家的目录模式完全一致；各专家的 Port、Adapter、Agent 目录独立，互不干扰。

### 11. 实现顺序与测试

- **选择**：实现顺序**灵活**。Tasks 按实现块组织（Research Domain/Ports/DTOs → 催化剂上下文构建 → 数据 Adapter → Agent + 解析 → Application 编排 → Presentation 路由 → 完整测试），**最后统一做完整测试**，确保所有 Spec Scenario 有对应通过测试。**无需 LLMPlatformContainer 扩展**（`web_search_service()` 已就绪）。
- **理由**：宏观情报员已铺平道路，催化剂侦探的实现更轻量（无上游前置变更），可直接聚焦 Research 内部代码。

## Risks / Trade-offs

| 风险 | 缓解 |
|------|------|
| Web 搜索结果不够聚焦个股（搜索公司名称可能返回同名其他公司或不相关结果） | 搜索查询同时包含公司名称和行业关键词以提高精确度；Prompt 严格约束 LLM 仅引用搜索结果中的信息；测试覆盖"搜索结果为空"Scenario。 |
| 部分维度搜索失败导致分析偏颇 | 每维度独立 try/except，失败维度返回空结果；ContextBuilder 标记"信息有限"；四维全部失败则拒绝分析（抛出 BadRequestException）。 |
| LLM 返回非 JSON 或格式不稳定（尤其 positive_catalysts/negative_catalysts 的嵌套结构更复杂） | Prompt 明确要求「仅输出纯 JSON 字符串、无 Markdown 标记」；解析内聚于 `agents/catalyst_detective/output_parser.py`，try/except + 日志；复用 `_strip_thinking_tags`；**测试覆盖「解析失败」Scenario**；使用 pydantic 做严格校验。 |
| 搜索 API 调用延迟（4 次顺序调用 × 每次 1-2 秒 ≈ 4-8 秒） | 当前可接受；若未来性能要求更高，可切换为 `asyncio.gather` 并发执行四次搜索。 |
| LLM 可能无视搜索证据，仍基于训练数据"幻觉"催化事件 | System Prompt 严格约束：「严禁引用搜索结果中未出现的事件、公告或数据」；output 中 `information_sources` 字段要求标注来源 URL。 |
| CatalystStockOverview 与 MacroStockOverview 字段完全相同，存在"代码重复"感 | 这是有意为之的设计决策（Decision 3），各专家 DTO 独立演进、互不耦合。若未来确认两者不会分化，可考虑提取公共基类，但当前维持独立。 |
| positive_catalysts/negative_catalysts 的嵌套结构增加 LLM 输出解析复杂度 | pydantic 严格校验嵌套结构；output_parser 中对缺失字段提供合理的错误信息；测试覆盖各种畸形 JSON 情况。 |

## Migration Plan

- **部署**：在已有 Research 模块上扩展，无存量数据迁移。不修改任何上游模块。引入新依赖通过依赖注入在应用启动时装配。
- **回滚**：催化剂侦探为独立新增能力，回滚即停止调用该 Application 接口；不影响已有四专家。

## Open Questions

- 搜索查询模板是否需要支持可配置（如从配置文件或环境变量读取），还是先硬编码在 Adapter 中？初步决定硬编码，通过代码迭代优化。
- 四个维度的搜索条数（当前 `count=8`）是否需要可配置？初步决定默认值，可通过参数覆盖。
- **催化事件的时效性与缓存**：催化事件本质上是实时的，同一标的在不同时间点的催化剂可能完全不同。与宏观分析（行业级、天/周级变化频率）不同，催化剂分析不适合做长时间缓存。本变更不实现缓存，保持最简的 `run(symbol)` 按需计算接口。
