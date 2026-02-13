# Design: Research 模块 — 宏观情报员

## Context

Research 是愿景中的「事实工厂」Bounded Context，代码库中已存在（`src/modules/research/`），其中**技术分析师**、**财务审计员**与**估值建模师**能力已实现并通过验收。本变更是 Research 的第四个子能力：**宏观情报员**，负责从自上而下的视角，通过 Web 搜索获取实时宏观动态（货币政策、产业政策、宏观经济周期、行业景气），结合 LLM 进行定性分析，输出结构化的宏观环境评估（Favorable / Neutral / Unfavorable + 四维分析），供后续 Debate/Judge 使用。

**与已有三专家的核心差异**：
- 技术分析师、财务审计员、估值建模师均消费 data_engineering 的**硬数据**（行情、财报、估值指标）。
- 宏观情报员的主要数据源是 llm_platform 的 **`WebSearchService`（软情报）**，这是 Research 模块**首次消费 Web 搜索能力**，实现了愿景中「证据驱动：观点必须基于硬数据（DB）或**软情报（搜索）**」的架构承诺。
- 宏观情报员无数值预计算（不同于估值建模师的分位点/PEG/Graham），"处理"环节是将多主题搜索结果结构化为维度对齐的文本上下文。

**约束**：模块间调用必须通过被调用模块的 **Application 接口**，不得直接依赖对方领域模型或 Infrastructure。Research 依赖 data_engineering（股票信息）、llm_platform（Web 搜索 + LLM）。

**已有资产**：
- 三专家已建立的模块骨架（domain/ports、application、infrastructure/adapters、agents/ 结构），可复用 `ILLMPort`、`prompt_loader` 加载模式、`LLMOutputParseError` 等公共设施。
- llm_platform 已有 `WebSearchService`（Application 接口）、`WebSearchRequest`/`WebSearchResponse` DTO（含 `to_prompt_context()` 方法）、`BochaWebSearchAdapter` 实现。
- data_engineering 已有 `GetStockBasicInfoUseCase` → `StockBasicInfoDTO(info: StockInfo, daily: StockDaily)`。
- 宏观情报员的 System Prompt 与 User Prompt 模板**已预先定义**（见 `system.md` 与 `user.md`）。

**相关方**：Coordinator（未来编排 Research）、Debate/Judge（消费 ResearchReport）；本变更仅实现宏观情报员单元，不实现编排与报告聚合。

**测试约束**：Spec 中每个 Scenario 在交付时须有对应自动化测试；实现顺序灵活（可先实现再补测）。设计决策须考虑可测性（Port、DI、DTO），便于补测或按需 TDD。

## Goals / Non-Goals

**Goals:**

- 在 `src/modules/research/` 下新增宏观情报员能力，复用已有模块骨架与公共设施（`ILLMPort`、prompt 加载模式、`LLMOutputParseError`）。
- 宏观情报员通过 **Application 接口** 调用 data_engineering（获取股票基础信息）、llm_platform（Web 搜索 + LLM 调用），不直接依赖其 Domain/Infrastructure。
- 输入：股票代码（symbol）；系统自动获取股票基础信息（名称/行业），并基于行业上下文执行多主题 Web 搜索。搜索结果在 Research 内部经过结构化处理后填入 User Prompt。输出：固定结构 JSON（macro_environment、confidence_score、macro_summary、dimension_analyses、key_opportunities、key_risks、information_sources）。
- 对外暴露独立 Application 入口（`MacroIntelligenceService`），与其他三专家接口形态一致但各自独立。HTTP 响应体 SHALL 包含 input、output、macro_indicators（代码塞入的宏观上下文快照），与 technical_indicators / financial_indicators / valuation_indicators 结构对称。
- **可测性**：通过 Port 抽象与依赖注入，使 Application 层在无真实下游时可仅用 mock 验证行为；每个 Spec Scenario 可映射为可执行测试。

**Non-Goals:**

- 不实现 Coordinator、Debate、Judge；不实现 Research 的「并行五专家」编排与完整 ResearchReport 聚合。
- 不实现剩余专家（催化剂侦探）。
- 不改变技术分析师、财务审计员与估值建模师的现有实现。
- 不实现自定义搜索引擎或爬虫（使用 llm_platform 已有的 WebSearchService）。

## Decisions

### 1. 数据来源：data_engineering（股票信息）+ llm_platform（Web 搜索 + LLM）

- **选择**：宏观情报员需要两类数据，分别来自两个上游模块：

  | 数据类别 | 上游模块 | 接口 | 状态 |
  |----------|---------|------|------|
  | 股票基础信息（名称、行业） | data_engineering | `GetStockBasicInfoUseCase` → `StockBasicInfoDTO` | **已有** |
  | 宏观情报搜索结果 | llm_platform | `WebSearchService.search(WebSearchRequest)` → `WebSearchResponse` | **已有** |
  | LLM 分析 | llm_platform | `LLMService.generate(prompt, system_message)` → `str` | **已有**（通过 `ILLMPort`） |

  **无需新增上游接口**。所有所需接口均已就绪。

- **理由**：与财务审计员（需新增 data_engineering 查询接口）和估值建模师（需新增估值日线查询 + bps 字段）不同，宏观情报员的数据需求完全被现有接口覆盖。这是五专家中**上游依赖最轻**的一个。

### 2. Domain 层三个抽象与跨模块调用

- **选择**：Research Domain 层包含三类与宏观情报员相关的抽象，延续已有三专家的三层 Port 模式（数据获取 → 数据处理 → Agent 分析）：

  1. **获取宏观所需数据**：Port（`IMacroDataPort`），包含两个方法：
     - `get_stock_overview(symbol) -> Optional[MacroStockOverview]`：获取股票基础信息（名称、行业、third_code）。Adapter 内部调用 `GetStockBasicInfoUseCase`，提取所需字段转为 Research 内部 DTO。返回 None 表示标的不存在。
     - `search_macro_context(industry, stock_name) -> List[MacroSearchResult]`：基于行业与公司上下文执行多主题宏观搜索。Adapter 内部调用 llm_platform 的 `WebSearchService`，按四个维度分别构建搜索查询，汇总返回。每个 `MacroSearchResult` 包含维度标识（dimension_topic）与该维度下的搜索结果条目列表。

  2. **构建宏观上下文**：Port（`IMacroContextBuilder`），入参为 `MacroStockOverview` + `List[MacroSearchResult]`，出参为 `MacroContextDTO`（与 User Prompt 模板占位符一一对应）。**处理逻辑在 Infrastructure 层实现**（见 Decision 4）。

  3. **宏观分析**：Port（`IMacroIntelligenceAgentPort`），入参为 `MacroContextDTO`，出参为 `MacroIntelligenceAgentResult`（含解析后的 `MacroIntelligenceResultDTO` + 原始 LLM 输出 + user prompt）。实现层负责加载/填充 Prompt、调用 LLM、解析结果。

  跨模块时，Research 的 Infrastructure Adapter 仅通过 data_engineering 的 **Application 接口**（`GetStockBasicInfoUseCase`）和 llm_platform 的 **Application 接口**（`WebSearchService`、`LLMService`）获取数据或调用能力，不引用对方 domain 或 infrastructure。

- **理由**：与已有三专家保持一致的三层 Port 模式，Domain 只定义「做什么」的契约，实现在 Infrastructure；Application 编排仅依赖 Domain Port，符合依赖倒置与可测性。`IMacroDataPort` 虽然内部调用两个不同上游模块，但对 Application 层而言只是一个「数据获取」关注点，保持注入依赖数量一致（3 个 Port）。

### 3. Research 对 Coordinator 暴露的 Application 接口：按专家独立、不共用

- **选择**：延续已有三专家的模式。本变更对外仅暴露宏观情报员专属入口 `MacroIntelligenceService.run(symbol)`。Coordinator 编排时分别调用各专家的 Application 接口。**Application 与 HTTP 响应体**：返回结果 SHALL 包含解析后的宏观情报 DTO 及 input、output、macro_indicators（代码塞入），与技术分析师的 technical_indicators、财务审计员的 financial_indicators、估值建模师的 valuation_indicators 结构对称。
- **理由**：每个专家入参/出参与职责不同，独立接口便于契约清晰、单独编写测试与演进。

### 4. 宏观上下文构建：文本结构化而非数值预计算

- **选择**：`IMacroContextBuilder` 的 Infrastructure 实现将股票概览与搜索结果转为 `MacroContextDTO`，具体处理逻辑：

  1. **按维度归类**：将 `List[MacroSearchResult]`（每个已标注 dimension_topic）按四个维度归类，每个维度的搜索结果转为格式化的文本段落（标题 + 来源 + 日期 + 摘要/内容）。
  2. **来源 URL 收集**：从所有搜索结果中提取去重的 URL 列表，作为 `all_source_urls`，供 LLM 在输出中引用。
  3. **空结果处理**：若某维度搜索返回 0 条结果，该维度的上下文标记为"该维度暂无搜索结果，信息有限"；LLM Prompt 已约定遇到信息不足时须声明并降低置信度。
  4. **输出 `MacroContextDTO`**：各字段与 User Prompt 模板占位符一一对应，包含：`stock_name`、`third_code`、`industry`（均从 `MacroStockOverview` 透传）、`current_date`（构建时由代码生成，格式如"2026-02-13"）、`monetary_context`（货币与流动性搜索摘要）、`policy_context`（产业政策搜索摘要）、`economic_context`（宏观经济搜索摘要）、`industry_context`（行业景气搜索摘要）、`all_source_urls`（来源 URL 列表字符串）。共 9 个字段，与 `user.md` 模板中的 9 个 `{...}` 占位符一一对应。

- **理由**：与估值建模师的数值预计算不同，宏观情报员的"处理"是文本结构化——将散乱的搜索结果组织为维度对齐的上下文。封装在 Infrastructure 实现中，通过 Domain Port 暴露，Application 不关心文本格式化细节；便于测试（mock Port 返回固定上下文）与后续调整格式。

### 5. 搜索策略：四维度 × 动态查询 × 时效过滤

- **选择**：`MacroDataAdapter` 的 `search_macro_context` 方法按四个维度构建搜索查询并执行：

  | 维度 | 查询模板（示例） | freshness |
  |------|----------------|-----------|
  | 货币与流动性 | `"{year}年 中国 央行 货币政策 利率 流动性"` | `oneMonth` |
  | 产业政策与监管 | `"{industry} 产业政策 监管政策 {year}年"` | `oneMonth` |
  | 宏观经济周期 | `"中国 宏观经济 GDP CPI PMI 经济数据 {year}年"` | `oneMonth` |
  | 行业景气与资金流向 | `"{industry} 行业景气 发展趋势 市场前景 {year}年"` | `oneMonth` |

  每个查询使用 `count=8`（每维度最多 8 条结果），启用 AI 摘要（`summary=True`）。四次搜索**顺序执行**（避免并发对搜索 API 产生压力，总计约 4 次 HTTP 调用）。

  搜索查询由代码根据 `industry`（来自 `MacroStockOverview`）和 `当前年份` 动态生成。`stock_name` 可选择性用于行业相关查询中增加精确度。

- **备选**：并发执行四次搜索（`asyncio.gather`）。
- **理由**：顺序执行简单可靠，四次搜索的总延迟在可接受范围内（约 2-4 秒）；避免对搜索 API 产生瞬时并发压力。若未来性能成为瓶颈，可轻松切换为 `asyncio.gather` 并发。

### 6. Web 搜索错误的优雅降级

- **选择**：`MacroDataAdapter` 中的每个维度搜索独立 try/except：若某维度搜索失败（网络超时、API 错误等），记录警告日志，该维度返回空结果（`MacroSearchResult(dimension_topic=..., items=[])`），**不中断整体分析流程**。搜索结果部分缺失时，`MacroContextBuilder` 标记对应维度为"信息有限"，LLM 在分析时会据此降低置信度。
- **全部搜索失败时**：若四个维度全部搜索失败（0 条搜索结果），`MacroIntelligenceService` SHALL 抛出 `BadRequestException`，明确告知调用方"宏观搜索全部失败，无法进行宏观分析"，而非将空上下文送入 LLM。
- **理由**：宏观分析是定性的，部分信息缺失仍可给出有限但诚实的判断；全部失败则无法提供有价值的分析。优雅降级提高了系统的容错性。

### 7. Prompt 资源复用已有模式

- **选择**：宏观情报员的 System Prompt 与 User Prompt 模板存放在 `src/modules/research/infrastructure/agents/macro_intelligence/prompts/`（`system.md` 与 `user.md`），运行时通过与已有专家相同的加载模式读取。在 `prompt_loader.py` 中新增宏观情报员的加载与填充函数。User Prompt 使用 `{...}` 单花括号占位符（Python `str.format()` 风格），与已有三专家一致。**Prompt 内容已预先定义**，实现时直接从 `openspec/changes/research-macro-intelligence/` 下的 `system.md` 与 `user.md` 拷贝至资源目录。
- **理由**：复用已有 prompt 加载基础设施模式，避免重复建设；占位符风格统一。

### 8. LLM 调用与输出解析

- **选择**：复用已有 `ILLMPort`（llm_platform 的 `LLMService.generate`）传入 System Prompt 与填充后的 User Prompt；要求模型仅输出纯 JSON。**宏观情报员的 JSON 结构与其他专家不同**，解析逻辑内聚到 `agents/macro_intelligence/output_parser.py`。Domain 层定义输出 DTO（`MacroIntelligenceResultDTO`），包含：
  - `macro_environment`：Literal（"Favorable (有利)" / "Neutral (中性)" / "Unfavorable (不利)"）
  - `confidence_score`：float（0.0–1.0），基于证据充分性与一致性
  - `macro_summary`：str（宏观环境综合判断，须引用搜索证据）
  - `dimension_analyses`：list，每个维度含 `dimension`（维度名）、`assessment`（评估）、`score`（0–100 该维度评分）、`key_findings`（关键发现列表）
  - `key_opportunities`：list[str]（宏观机会列表）
  - `key_risks`：list[str]（宏观风险列表）
  - `information_sources`：list[str]（引用的信息来源 URL 列表）

  解析失败时记录日志（含 LLM 原始输出，可截断）并抛出 `LLMOutputParseError`。输出解析器复用 `_strip_thinking_tags`（剥离 `<think>` 标签）和 markdown 代码块剥离逻辑。

- **理由**：各 Agent 返回的 JSON 结构不同，解析内聚到 Agent 可避免共享解析层膨胀；复用已有领域异常；单元测试可针对 output_parser 单独测。

### 9. 独立 MacroStockOverview DTO（不复用 StockOverviewInput）

- **选择**：为宏观情报员新增专属输入 DTO `MacroStockOverview`，仅包含 `stock_name`、`industry`、`third_code` 三个字段。不复用估值建模师的 `StockOverviewInput`（含 current_price、total_mv、pe_ttm、pb 等估值字段）。
- **备选**：复用 `StockOverviewInput`，忽略多余字段。
- **理由**：宏观情报员不需要价格/市值/估值数据，独立 DTO 语义清晰，避免耦合到估值特定的数据结构；各专家的输入 DTO 独立演进，互不影响。

### 10. LLMPlatformContainer 新增 web_search_service() 工厂方法

- **选择**：在 `LLMPlatformContainer` 中新增 `web_search_service()` 方法，返回装配好的 `WebSearchService` 实例。Research 的 `ResearchContainer` 通过 `_llm_container.web_search_service()` 获取搜索服务，注入到 `MacroDataAdapter` 中。
- **备选**：Research 直接导入 llm_platform 的 Infrastructure（`BochaWebSearchAdapter`、`llm_config`）自行构造。
- **理由**：遵循已有模式——Research 通过 `LLMPlatformContainer` 获取 llm_platform 能力（如 `llm_service()`），而非直接导入其 Infrastructure。`web_search_service()` 是一个非破坏性的容器扩展，不改变任何现有行为。

### 11. 目录与分层结构

- **选择**：在 `src/modules/research/` 已有结构上扩展：
  - **domain/dtos/macro_inputs.py**：新增 `MacroStockOverview`、`MacroSearchResultItem`、`MacroSearchResult`。
  - **domain/dtos/macro_context.py**：新增 `MacroContextDTO`（9 个字段与 User Prompt 模板占位符一一对应：stock_name、third_code、industry、current_date、monetary_context、policy_context、economic_context、industry_context、all_source_urls）。
  - **domain/dtos/macro_dtos.py**：新增 `MacroIntelligenceResultDTO`、`MacroDimensionAnalysis`、`MacroIntelligenceAgentResult`。
  - **domain/ports/macro_data.py**：`IMacroDataPort`（2 个方法：get_stock_overview + search_macro_context）。
  - **domain/ports/macro_context_builder.py**：`IMacroContextBuilder`。
  - **domain/ports/macro_intelligence_agent.py**：`IMacroIntelligenceAgentPort`。
  - **application/macro_intelligence_service.py**：编排「校验 → 获取股票概览（校验非空）→ 执行宏观搜索 → 校验搜索结果非全空 → 构建宏观上下文 → 调用 Agent → 返回完整响应」。
  - **infrastructure/adapters/macro_data_adapter.py**：实现 `IMacroDataPort`（内部调用 data_engineering `GetStockBasicInfoUseCase` + llm_platform `WebSearchService`）。
  - **infrastructure/adapters/macro_intelligence_agent_adapter.py**：实现 `IMacroIntelligenceAgentPort`（加载 Prompt + 调用 LLM + 解析）。
  - **infrastructure/macro_context/context_builder.py**：实现 `IMacroContextBuilder`（结构化搜索结果为维度对齐上下文）。
  - **infrastructure/agents/macro_intelligence/prompts/**：`system.md`、`user.md`。
  - **infrastructure/agents/macro_intelligence/output_parser.py**：解析 LLM JSON 输出。
  - **presentation/rest/macro_intelligence_routes.py**：宏观情报员 REST 路由，通过 FastAPI `Depends` 装配 `MacroIntelligenceService` 所需的全部 Port 实现，处理异常（BadRequestException→400、LLMOutputParseError→422、其他→500），与已有三专家路由同级同模式。
- **理由**：与技术分析师、财务审计员、估值建模师的已有目录模式一致；各专家的 Port、Adapter、Agent 目录独立，互不干扰。

### 12. 实现顺序与测试

- **选择**：实现顺序**灵活**：可先实现再在交付前补全测试，也可在关键逻辑处先写测试再实现。Tasks 按实现块组织（LLMPlatformContainer 扩展 → Research Domain/Ports/DTOs → 宏观上下文构建 → Agent + 解析 → Application 编排 → Presentation 路由 → 完整测试），**最后统一做完整测试**，确保所有 Spec Scenario 有对应通过测试。
- **理由**：在保证可验证性的前提下减少步骤、加快执行；设计已考虑可测性（Port、DTO），便于补测。

## Risks / Trade-offs

| 风险 | 缓解 |
|------|------|
| Web 搜索结果质量不稳定（与结构化硬数据不同，搜索结果可能不相关或过时） | 使用 `freshness=oneMonth` 过滤时效；启用 AI 摘要（`summary=True`）提高信息密度；Prompt 明确要求 LLM 仅引用搜索结果中的信息，遇到信息不足时声明并降低置信度；测试覆盖"搜索结果为空"Scenario。 |
| 部分维度搜索失败导致分析偏颇 | 每维度独立 try/except，失败维度返回空结果；ContextBuilder 标记"信息有限"；四维全部失败则拒绝分析（抛出 BadRequestException）。 |
| LLM 返回非 JSON 或格式不稳定 | Prompt 明确要求「仅输出纯 JSON 字符串、无 Markdown 标记」；解析内聚于 `agents/macro_intelligence/output_parser.py`，try/except + 日志；复用 `_strip_thinking_tags`；**测试覆盖「解析失败」Scenario**。 |
| 搜索 API 调用延迟（4 次顺序调用 × 每次 1-2 秒 ≈ 4-8 秒） | 当前可接受；若未来性能要求更高，可切换为 `asyncio.gather` 并发执行四次搜索。 |
| LLM 可能无视搜索证据，仍基于训练数据"幻觉"宏观判断 | System Prompt 严格约束：「你只能引用 [搜索证据] 中提供的信息」「禁止引用未在搜索结果中出现的数据或事件」；output 中 `information_sources` 字段要求标注来源 URL。 |
| `LLMPlatformContainer` 新增方法可能影响其他消费方 | `web_search_service()` 为新增方法，不修改任何已有方法签名或行为；对已有消费方零影响。 |
| 搜索查询模板可能不够精准（行业名称过于宽泛或过于细分） | 查询模板在 Adapter 中集中定义，易于调整；初期使用通用模板，根据实际搜索效果迭代优化。 |

## Migration Plan

- **部署**：在已有 Research 模块上扩展，无存量数据迁移。llm_platform 仅在 Container 中新增工厂方法（非破坏性）。引入新依赖通过依赖注入在应用启动时装配。
- **回滚**：宏观情报员为独立新增能力，回滚即停止调用该 Application 接口；llm_platform Container 新增的方法无副作用，可保留。

## Open Questions

- 搜索查询模板是否需要支持可配置（如从配置文件或环境变量读取），还是先硬编码在 Adapter 中？初步决定硬编码，通过代码迭代优化。
- 四个维度的搜索条数（当前 `count=8`）是否需要可配置？初步决定默认值，可通过参数覆盖。
- ~~Presentation 层（REST 路由）是否在本变更中实现？~~ **已确认：必须实现**。路由位于 `presentation/rest/macro_intelligence_routes.py`，与已有三专家同级同模式。
- **宏观分析的行业级缓存与定时刷新**：宏观分析本质上是行业级别的（非个股级别），同行业的不同标的会得到几乎相同的宏观评估；且宏观因素变化频率为天/周级别。因此宏观分析天然适合以 `(industry, date)` 为 key 做日级缓存或定时预计算。但缓存策略与定时调度属于 **Coordinator 编排层**的职责（Research 是被动的事实工厂），且需要持久化层支撑。**本变更不实现缓存**，保持最简的 `run(symbol)` 按需计算接口；在 Coordinator 变更中统一设计缓存/预计算策略。
