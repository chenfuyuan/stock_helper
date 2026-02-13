# Spec: research-macro-intelligence

宏观情报员能力：从自上而下视角，通过 Web 搜索获取实时宏观动态（货币政策、产业政策、宏观经济周期、行业景气），结合 LLM 进行定性分析，输出结构化的宏观环境评估（Favorable / Neutral / Unfavorable + 四维分析 JSON），供 Debate/Judge 使用。Research 对 Coordinator 按专家暴露独立 Application 接口，本 spec 仅约束宏观情报员。

**核心特点**：这是 Research 五专家中唯一以**软情报（Web 搜索）**为主要数据源的角色。系统基于标的行业上下文动态生成搜索查询，按四个维度获取实时宏观情报，LLM 仅基于搜索结果进行定性分析，**禁止引用搜索结果中未出现的数据或事件**。

**测试约定**：每个 `#### Scenario:` 在变更**交付时**须对应至少一个自动化测试用例（单元或集成）；实现顺序可先实现再补测，以完整测试通过为需求完成标准。

---

## Requirements

### Requirement: 宏观情报员暴露独立 Application 接口

Research 模块 SHALL 为宏观情报员暴露独立的 Application 层入口（如 `MacroIntelligenceService`），供 Coordinator 直接调用。该接口 SHALL NOT 与其他四专家共用同一入口；Coordinator 编排时 SHALL 分别调用各专家的专属 Application 接口。

#### Scenario: Coordinator 调用宏观情报员

- **WHEN** Coordinator 需要该标的的宏观面评估
- **THEN** Coordinator 调用宏观情报员的 Application 接口（入参含 symbol），获得宏观分析结果 DTO，且不通过统一的「Research 总入口」

#### Scenario: 接口入参与出参为 DTO

- **WHEN** 调用宏观情报员 Application 接口
- **THEN** 入参为 DTO 或值对象（至少包含 symbol），出参为宏观分析结果 DTO（对应下方输出契约），不暴露 Research 内部领域模型

---

### Requirement: Presentation 层 REST 路由

Research 模块 SHALL 为宏观情报员暴露 HTTP REST 接口（路由路径如 `GET /api/v1/research/macro-intelligence`），位于 `src/modules/research/presentation/rest/` 下，与技术分析师（`technical_analyst_routes.py`）、财务审计员（`financial_auditor_routes.py`）和估值建模师（`valuation_modeler_routes.py`）同级。该路由 SHALL 通过 FastAPI 依赖注入装配 `MacroIntelligenceService` 所需的全部 Port 实现（`IMacroDataPort`、`IMacroContextBuilder`、`IMacroIntelligenceAgentPort`），并在路由函数中调用 `MacroIntelligenceService.run(symbol)`。

路由 SHALL 处理以下异常并返回对应 HTTP 状态码：
- `BadRequestException` → 400
- `LLMOutputParseError` → 422
- 其他未预期异常 → 500（记录日志）

#### Scenario: HTTP 接口可正常调用

- **WHEN** 发送 `GET /api/v1/research/macro-intelligence?symbol=000001.SZ` 请求
- **THEN** 系统 SHALL 通过依赖注入装配服务并返回宏观分析结果，HTTP 状态码为 200

#### Scenario: symbol 缺失或无效时返回 400

- **WHEN** 发送请求时 symbol 为空或缺失
- **THEN** 系统 SHALL 返回 HTTP 400，响应体包含可区分的错误信息

#### Scenario: LLM 解析失败时返回 422

- **WHEN** 大模型返回无法解析的内容
- **THEN** 系统 SHALL 返回 HTTP 422，响应体包含解析失败信息

---

### Requirement: HTTP 响应体包含 input、output、macro_indicators

宏观情报员 HTTP 接口的响应体 SHALL 与技术分析师/财务审计员/估值建模师接口一致，由**代码塞入**以下字段（非大模型拼接）：`input`（送入大模型的 user prompt）、`output`（大模型原始返回字符串）、`macro_indicators`（宏观上下文快照，用于填充 prompt 的 `MacroContextDTO` 序列化结果）。响应体 SHALL 同时包含解析后的宏观分析结果字段（macro_environment、confidence_score、macro_summary、dimension_analyses、key_opportunities、key_risks、information_sources）。

#### Scenario: 响应体含 input、output、macro_indicators

- **WHEN** 调用宏观情报 HTTP 接口并成功返回
- **THEN** 响应体 SHALL 包含 `input`（字符串）、`output`（字符串）、`macro_indicators`（对象），便于调试与审计追溯

#### Scenario: 与其他专家接口结构对称

- **WHEN** 比较技术分析师、财务审计员、估值建模师与宏观情报员的 HTTP 响应结构
- **THEN** 四者 SHALL 均包含 input、output，且分别包含 `technical_indicators`、`financial_indicators`、`valuation_indicators`、`macro_indicators`，结构对称

---

### Requirement: 输入契约 — 股票代码与多源数据自动获取

宏观情报员 SHALL 接受股票代码（symbol）作为主要输入。系统 SHALL 自动：
1. 从 data_engineering 获取该标的的**股票基础信息**（名称 stock_name、行业 industry、代码 third_code）—— 通过已有的 `GetStockBasicInfoUseCase`。
2. 基于行业与公司上下文，通过 llm_platform 的 `WebSearchService` 执行**多主题宏观搜索**，获取实时宏观情报。

宏观情报员 SHALL NOT 在观点中引用或捏造 Web 搜索结果中不存在的数据或事件。

#### Scenario: 输入完整时产出有效结果

- **WHEN** 调用方提供有效的 symbol，且 data_engineering 中存在该标的的股票基础信息，且 Web 搜索返回了相关结果
- **THEN** 宏观情报员返回符合输出契约的 JSON 结果，且 macro_summary 和 key_findings 中引用的信息均来自 Web 搜索结果

#### Scenario: 输入缺失 symbol 时的行为

- **WHEN** 调用方未提供必填输入 symbol（空字符串或 None）
- **THEN** 系统 SHALL 在调用 Application 接口时通过校验或领域异常明确拒绝，并返回可区分的错误信息

#### Scenario: 该标的不存在时的行为

- **WHEN** 调用方提供的 symbol 在 data_engineering 中无对应股票基础信息
- **THEN** 系统 SHALL 返回明确的错误信息（如「该标的不存在」），不继续后续搜索

---

### Requirement: 多维度宏观搜索策略

宏观情报员 SHALL 基于标的行业上下文，按**四个宏观维度**分别构建搜索查询并执行 Web 搜索：
1. **货币与流动性环境**：央行货币政策、利率、流动性相关
2. **产业政策与监管动态**：该行业的产业政策、监管政策相关
3. **宏观经济周期定位**：GDP、CPI、PMI 等宏观经济指标相关
4. **行业景气与资金流向**：该行业的景气度、发展趋势、市场前景相关

搜索查询 SHALL 由代码根据标的行业（industry）和当前年份动态生成。每个维度的搜索 SHALL 使用时效过滤（如 `freshness=oneMonth`）以获取近期信息，并启用 AI 摘要。

#### Scenario: 按四个维度分别搜索

- **WHEN** 宏观情报员执行分析流程并需要获取宏观情报
- **THEN** 系统 SHALL 针对四个维度分别执行 Web 搜索（共 4 次搜索调用），每次搜索的查询词包含标的行业上下文

#### Scenario: 搜索查询包含行业上下文

- **WHEN** 标的属于"银行"行业
- **THEN** 产业政策维度的搜索查询 SHALL 包含"银行"关键词；行业景气维度的搜索查询 SHALL 包含"银行"关键词

#### Scenario: 搜索使用时效过滤

- **WHEN** 系统执行宏观搜索
- **THEN** 搜索请求 SHALL 设置 freshness 参数（如 `oneMonth`），以获取近期宏观信息而非过时数据

---

### Requirement: 宏观搜索的优雅降级

宏观搜索过程中，单个维度的搜索失败（网络超时、API 错误等）SHALL NOT 导致整体分析中断。系统 SHALL 按以下规则处理搜索异常：
- 单维度搜索失败时，记录警告日志，该维度返回空结果，其他维度正常继续。
- 全部四个维度搜索均失败（0 条结果）时，系统 SHALL 抛出明确错误，不将空上下文送入 LLM。

#### Scenario: 单维度搜索失败不中断分析

- **WHEN** 四个维度中有 1-3 个维度搜索失败（返回异常），其余维度正常返回结果
- **THEN** 系统 SHALL 继续执行分析，失败维度在上下文中标记为"信息有限"，LLM 基于可用信息给出判断

#### Scenario: 全部搜索失败时拒绝分析

- **WHEN** 四个维度的搜索全部失败（0 条搜索结果）
- **THEN** 系统 SHALL 返回明确的错误信息（如「宏观搜索全部失败，无法进行宏观分析」），不将空上下文送入 LLM

---

### Requirement: 宏观上下文构建为 Domain Port、Infrastructure 实现

宏观情报员所需的结构化宏观上下文 SHALL 通过 Research Domain 层定义的「构建宏观上下文」Port（如 `IMacroContextBuilder`）获得：该 Port 入参为 `MacroStockOverview`（股票基础信息）和 `List[MacroSearchResult]`（多维度搜索结果），出参为与 User Prompt 模板一致的 `MacroContextDTO`。Port 的具体实现 SHALL 位于 Research 的 Infrastructure 层。

实现 SHALL 包含以下处理：
1. 按四个维度归类搜索结果，将每个维度的搜索条目格式化为带标题、来源、日期的文本段落。
2. 从全部搜索结果中提取去重的 URL 列表，作为 `all_source_urls`。
3. 若某维度搜索返回 0 条结果，该维度上下文 SHALL 标记为"该维度暂无搜索结果，信息有限"。

Application 层 SHALL 仅依赖该 Port 获取上下文，SHALL NOT 直接调用 Infrastructure 中的构建实现。

#### Scenario: 通过 Port 获取宏观上下文

- **WHEN** Application 编排需要构建宏观上下文以进行宏观分析
- **THEN** 通过注入的上下文构建 Port（如 `IMacroContextBuilder`）传入股票概览与搜索结果并获取 `MacroContextDTO`，不直接实例化或引用 Infrastructure 中的构建实现

#### Scenario: 搜索结果按维度归类格式化

- **WHEN** 上下文构建器收到包含四个维度搜索结果的列表
- **THEN** 输出上下文中的 `monetary_context`、`policy_context`、`economic_context`、`industry_context` SHALL 分别包含对应维度的格式化搜索摘要

#### Scenario: 空维度标记为信息有限

- **WHEN** 某维度搜索返回 0 条结果
- **THEN** 上下文构建器 SHALL 将该维度的上下文标记为"该维度暂无搜索结果，信息有限"，SHALL NOT 留空或抛出异常

#### Scenario: 来源 URL 收集与去重

- **WHEN** 上下文构建器处理多维度搜索结果
- **THEN** 输出上下文的 `all_source_urls` SHALL 包含所有搜索结果条目的去重 URL 列表

---

### Requirement: 输出契约 — 固定 JSON 结构

宏观情报员的产出 SHALL 为固定结构的 JSON（或等价的 DTO），包含：

- `macro_environment`（枚举：Favorable (有利) / Neutral (中性) / Unfavorable (不利)）
- `confidence_score`（float，0.0–1.0），基于证据充分性与一致性打分
- `macro_summary`（str），宏观环境综合判断，须引用搜索证据
- `dimension_analyses`（list，包含 4 个维度，每个维度含 `dimension`（维度名）、`assessment`（评估）、`score`（0–100 该维度评分）、`key_findings`（关键发现列表））
- `key_opportunities`（list[str]），宏观层面的机会
- `key_risks`（list[str]），宏观层面的风险
- `information_sources`（list[str]），引用的信息来源 URL 列表，用于溯源审计

**解析逻辑 SHALL 内聚到该 Agent**（`agents/macro_intelligence/output_parser.py`）。系统 SHALL 使用 pydantic 或等价机制校验并反序列化本 Agent 的 LLM 输出。若解析失败 SHALL **将 LLM 原始输出写入日志（可截断）** 并抛出领域友好异常（`LLMOutputParseError`），不将未校验的字符串作为宏观分析结果返回给调用方。

#### Scenario: 正常返回符合结构的结果

- **WHEN** LLM 返回合法且可解析的 JSON
- **THEN** Application 层返回的 DTO 包含上述七类字段，且 macro_environment 为三值之一、confidence_score 在 [0, 1] 内、dimension_analyses 包含 4 个维度、key_opportunities 和 key_risks 为非空列表、information_sources 包含至少一个 URL

#### Scenario: LLM 返回非 JSON 或格式错误

- **WHEN** LLM 返回内容无法解析为上述结构的 JSON
- **THEN** 系统 SHALL 将 LLM 原始输出写入日志（可截断）、抛出 `LLMOutputParseError`，不将未校验的字符串作为宏观分析结果返回给调用方

#### Scenario: LLM 返回含 thinking 标签

- **WHEN** LLM 返回内容包含 `<think>...</think>` 标签（reasoning model 的思考过程）
- **THEN** 输出解析器 SHALL 先剥离 thinking 标签再尝试 JSON 解析，不因 thinking 标签导致解析失败

---

### Requirement: 证据驱动与无交易建议

宏观情报员的观点（macro_summary、dimension_analyses 中的 assessment 与 key_findings、key_opportunities、key_risks）SHALL 直接引用 Web 搜索获取的具体信息作为证据，并 SHALL 在 `information_sources` 中标注引用的来源 URL。宏观情报员 SHALL NOT 输出「建议买入」「建议卖出」「立即建仓」等交易指令；该类决策属于 Judge 模块职责。当搜索结果不足以支撑某维度判断时，LLM SHALL 明确声明"信息有限"并降低 confidence_score。

#### Scenario: 观点引用搜索证据

- **WHEN** Web 搜索结果中包含关于央行降息的信息
- **THEN** macro_summary 或 dimension_analyses 中引用该信息时 SHALL 与搜索结果一致，不得捏造未搜索到的政策或数据

#### Scenario: 不输出交易建议

- **WHEN** 宏观情报员生成 macro_summary 与 key_opportunities
- **THEN** 输出 SHALL NOT 包含建议买入、建议卖出、立即建仓等交易指令类表述

#### Scenario: 信息不足时声明并降低置信度

- **WHEN** 某维度的搜索结果为"信息有限"（0 条结果）
- **THEN** LLM 输出 SHALL 在该维度的 assessment 中明确声明"信息有限"或"数据不足"，且 confidence_score SHALL 相应降低

---

### Requirement: Prompt 内聚于 Agent 且存放于代码外

宏观情报员的 System Prompt 与 User Prompt 模板 SHALL 内聚在该专家（agent）的上下文中，且 SHALL NOT 将 prompt 正文硬编码在代码中。Prompt 内容 SHALL 存放在代码库内约定的资源目录（`src/modules/research/infrastructure/agents/macro_intelligence/prompts/` 下的 `system.md` 与 `user.md`），由该专家的 Infrastructure 在运行时加载；模板中的占位符（如 `{stock_name}`、`{industry}`、`{monetary_context}`、`{policy_context}`、`{economic_context}`、`{industry_context}`、`{all_source_urls}`）SHALL 在代码中用本次调用的宏观上下文数据填充，使用与其他专家一致的 Python `str.format()` 风格（`{...}` 单花括号）。

#### Scenario: Prompt 从资源加载

- **WHEN** 宏观情报员执行分析流程并需要调用 LLM
- **THEN** 使用的 System Prompt 与 User Prompt 模板来自资源文件（`agents/macro_intelligence/prompts/`），而非 Python 源码中的长字符串

#### Scenario: 占位符由代码填充

- **WHEN** 资源文件中的 User Prompt 包含占位符（如 `{stock_name}`、`{industry}`、`{monetary_context}`、`{policy_context}`）
- **THEN** 运行时由代码使用 `str.format()` 和本次调用的宏观上下文数据填充这些占位符后，再传入 LLM

---

### Requirement: 跨模块与模块内均通过 Port/Application 接口

宏观情报员实现 SHALL 仅通过 data_engineering 的 **Application 接口**（`GetStockBasicInfoUseCase`）获取股票信息，通过 llm_platform 的 **Application 接口**（`WebSearchService` 获取搜索结果、`LLMService` 调用 LLM）；SHALL NOT 直接依赖上述模块的领域模型、实体、值对象或 Infrastructure 实现。**Research 内部**对「获取宏观数据」「构建宏观上下文」「调用宏观 Agent」的依赖 SHALL 通过 Domain Port 进行，Application 层 SHALL NOT 直接依赖 Infrastructure 实现类。入参/出参 SHALL 使用 DTO 或 Port 约定的抽象类型。

#### Scenario: 获取股票基础信息

- **WHEN** 宏观情报员需要股票基础信息（名称、行业）
- **THEN** 通过 Research 的宏观数据 Port（`IMacroDataPort`，其 Adapter 内部调用 data_engineering 的 `GetStockBasicInfoUseCase`）获取 DTO，不直接依赖 data_engineering 的 repository 或 domain 实体

#### Scenario: 执行 Web 搜索

- **WHEN** 宏观情报员需要获取实时宏观情报
- **THEN** 通过 Research 的宏观数据 Port（`IMacroDataPort`，其 Adapter 内部调用 llm_platform 的 `WebSearchService`）执行搜索并获取 DTO 列表

#### Scenario: 调用 LLM

- **WHEN** 宏观情报员需要调用大模型生成宏观分析
- **THEN** 通过宏观 Agent Port（`IMacroIntelligenceAgentPort`，其实现内部调用 llm_platform 的 Application 接口）传入 system_message 与 prompt，Application 层不直接依赖 llm_platform 的 router、registry 或 adapter 实现类

---

### Requirement: 可测性 — Scenario 与测试一一对应

每个上述 Scenario 在变更交付时 SHALL 对应至少一个自动化测试（单元或集成）；需求完成的验收条件包含「该需求下所有 Scenario 的测试通过」。实现时可采用先实现再补测，不强制测试先行。

#### Scenario: 测试覆盖输入缺失拒绝

- **WHEN** 运行宏观情报员相关测试套件
- **THEN** 存在测试用例：传入缺失 symbol 的入参，断言调用被拒绝并返回可区分错误（对应「输入缺失 symbol 时的行为」）

#### Scenario: 测试覆盖标的不存在拒绝

- **WHEN** 运行宏观情报员相关测试套件
- **THEN** 存在测试用例：mock 数据 Port 返回 None（标的不存在），断言系统返回明确错误信息

#### Scenario: 测试覆盖全部搜索失败拒绝

- **WHEN** 运行宏观情报员相关测试套件
- **THEN** 存在测试用例：mock 搜索返回全部为空（0 条结果），断言系统返回明确错误信息（对应「全部搜索失败时拒绝分析」）

#### Scenario: 测试覆盖部分搜索失败降级

- **WHEN** 运行宏观情报员相关测试套件
- **THEN** 存在测试用例：mock 部分维度搜索失败、部分成功，断言系统正常继续分析且失败维度被标记为"信息有限"

#### Scenario: 测试覆盖 LLM 解析失败

- **WHEN** 运行宏观情报员相关测试套件
- **THEN** 存在测试用例：mock LLM 返回非 JSON 或非法结构，断言系统抛出 `LLMOutputParseError`、不返回未校验字符串

#### Scenario: 测试覆盖上下文构建

- **WHEN** 运行宏观情报员相关测试套件
- **THEN** 存在测试用例：传入已知搜索结果，断言上下文构建器输出的各维度文本正确归类、来源 URL 已去重收集、空维度已标记为"信息有限"
