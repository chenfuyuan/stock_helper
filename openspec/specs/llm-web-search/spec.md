# Spec: llm-web-search

llm_platform 模块的 Web 搜索网关能力：定义厂商无关的搜索抽象（Port）与标准输入/输出 DTO，实现博查 AI（Bocha AI）Web Search API 适配器，通过 Application 层 `WebSearchService` 对外暴露搜索入口，供 Research 等下游模块跨模块消费。该能力与 LLM 文本生成能力并列，完全独立，不修改现有 LLM 相关代码。

**测试约定**：每个 `#### Scenario:` 在变更**交付时**须对应至少一个自动化测试用例（单元或集成）；实现顺序可先实现再补测，以完整测试通过为需求完成标准。

---

## ADDED Requirements

### Requirement: 搜索 Port 独立于 LLM Port

llm_platform 的 Domain 层 SHALL 新增 Web Search Port（`IWebSearchProvider`，ABC），签名为 `async def search(request: WebSearchRequest) -> WebSearchResponse`。该 Port SHALL 与 `ILLMProvider` 完全独立，不存在继承关系。搜索与文本生成为不同能力域——输入/输出契约、底层 API、计费逻辑均不同，合并会违反接口隔离原则（ISP）。

#### Scenario: Port 定义独立于 LLM Port

- **WHEN** 查看 `llm_platform` 的 Domain Port 定义
- **THEN** `IWebSearchProvider` SHALL 为独立的 ABC，定义 `search(request: WebSearchRequest) -> WebSearchResponse` 方法，SHALL NOT 继承 `ILLMProvider`

#### Scenario: Port 签名使用厂商无关 DTO

- **WHEN** 调用 `IWebSearchProvider.search(request)`
- **THEN** 入参 SHALL 为 `WebSearchRequest`，出参 SHALL 为 `WebSearchResponse`，两者均为 Domain 层定义的厂商无关 DTO

---

### Requirement: 搜索 DTO 为厂商无关的标准定义

llm_platform 的 Domain 层 SHALL 定义以下搜索 DTO（Pydantic `BaseModel`）：

- **`WebSearchRequest`**：`query: str`（必填）、`freshness: Optional[str]`（时效过滤，可选值 `oneDay` / `oneWeek` / `oneMonth` / `oneYear` / `noLimit`，默认不限）、`summary: bool = True`（是否生成 AI 摘要）、`count: int = 10`（返回条数）。
- **`WebSearchResponse`**：`query: str`（原始查询词）、`total_matches: Optional[int]`（匹配总数）、`results: List[WebSearchResultItem]`（结果列表）。
- **`WebSearchResultItem`**：`title: str`、`url: str`、`snippet: str`、`summary: Optional[str]`（AI 摘要，请求 `summary=True` 时有值）、`site_name: Optional[str]`、`published_date: Optional[str]`。

所有 DTO SHALL 使用 Pydantic `BaseModel`，字段命名 SHALL NOT 绑定博查 API 的字段名（如博查的 `name` 映射为 DTO 的 `title`）。

#### Scenario: WebSearchRequest 包含完整搜索参数

- **WHEN** 构造搜索请求
- **THEN** `WebSearchRequest` SHALL 包含 `query`（str, 必填）、`freshness`（Optional[str]）、`summary`（bool, 默认 True）、`count`（int, 默认 10）字段

#### Scenario: WebSearchResponse 包含结果列表

- **WHEN** 搜索完成后构造响应
- **THEN** `WebSearchResponse` SHALL 包含 `query`（str）、`total_matches`（Optional[int]）、`results`（List[WebSearchResultItem]）字段

#### Scenario: WebSearchResultItem 包含结构化结果字段

- **WHEN** 解析单条搜索结果
- **THEN** `WebSearchResultItem` SHALL 包含 `title`（str）、`url`（str）、`snippet`（str）、`summary`（Optional[str]）、`site_name`（Optional[str]）、`published_date`（Optional[str]）字段

---

### Requirement: 博查 AI Web Search 适配器

llm_platform 的 Infrastructure 层 SHALL 实现 `BochaWebSearchAdapter`（实现 `IWebSearchProvider`），调用博查 AI Web Search API（`POST https://api.bochaai.com/v1/web-search`）。适配器 SHALL 使用 `httpx.AsyncClient` 发送异步 HTTP 请求，将 `WebSearchRequest` 转为博查 API 请求格式，将博查响应映射为 `WebSearchResponse`。

适配器构造函数 SHALL 接收 `api_key: str` 和 `base_url: str`（默认 `https://api.bochaai.com`），请求超时默认 30 秒。

响应映射规则：博查 `webPages.value[].name` → `title`、`url` → `url`、`snippet` → `snippet`、`summary` → `summary`、`siteName` → `site_name`、`datePublished` → `published_date`。

#### Scenario: 正常搜索返回映射结果

- **WHEN** 博查 API 返回正常的 `SearchResponse`（含 `webPages.value[]`）
- **THEN** 适配器 SHALL 将每条结果映射为 `WebSearchResultItem`（字段映射：`name` → `title`、`snippet` → `snippet`、`summary` → `summary`、`siteName` → `site_name`、`datePublished` → `published_date`），组装为 `WebSearchResponse` 返回

#### Scenario: 搜索无结果时返回空列表

- **WHEN** 博查 API 返回 `webPages` 为空或 `value` 为空列表
- **THEN** 适配器 SHALL 返回 `WebSearchResponse`，其 `results` 为空列表，SHALL NOT 抛出异常

#### Scenario: 请求参数正确传递

- **WHEN** 调用 `search()` 传入包含 `freshness`、`summary`、`count` 的 `WebSearchRequest`
- **THEN** 适配器 SHALL 将这些参数正确映射到博查 API 请求体中

---

### Requirement: 适配器错误处理与 Domain 异常

适配器 SHALL 将博查 API 调用过程中的错误映射为 Domain 异常：
- HTTP 4xx/5xx 响应 → 记录日志并抛出 `WebSearchError`。
- 网络超时 / 连接失败 → 抛出 `WebSearchConnectionError`。
- API Key 未配置（空字符串）→ 在调用时抛出 `WebSearchConfigError`。

Domain 层 SHALL 新增以下异常，继承 `AppException`：
- `WebSearchError`：通用搜索错误（API 返回错误码、响应格式异常）。
- `WebSearchConnectionError`：网络连接 / 超时错误。
- `WebSearchConfigError`：配置错误（API Key 未配置）。

#### Scenario: HTTP 错误码转为 WebSearchError

- **WHEN** 博查 API 返回 HTTP 4xx 或 5xx 状态码
- **THEN** 适配器 SHALL 记录错误日志并抛出 `WebSearchError`，异常消息 SHALL 包含 HTTP 状态码信息

#### Scenario: 网络超时转为 WebSearchConnectionError

- **WHEN** 调用博查 API 时发生网络超时或连接拒绝
- **THEN** 适配器 SHALL 抛出 `WebSearchConnectionError`

#### Scenario: API Key 未配置时抛出 WebSearchConfigError

- **WHEN** `api_key` 为空字符串时调用 `search()`
- **THEN** 适配器 SHALL 在调用时抛出 `WebSearchConfigError`，消息明确说明 API Key 未配置，SHALL NOT 在适配器构造时崩溃

#### Scenario: 响应格式异常时防御性处理

- **WHEN** 博查 API 返回的 JSON 结构缺少预期字段（如无 `webPages` 键）
- **THEN** 适配器 SHALL 做防御性解析（缺失字段给默认值），SHALL NOT 因字段缺失导致未处理异常

---

### Requirement: Application 层搜索服务

llm_platform 的 Application 层 SHALL 新增 `WebSearchService`，构造函数通过依赖注入接收 `IWebSearchProvider` 实例。`WebSearchService` SHALL 暴露 `async def search(request: WebSearchRequest) -> WebSearchResponse` 方法。

`WebSearchService` 当前 SHALL 做透传（调用注入的 Provider）+ 日志记录（搜索关键词、结果数量），SHALL NOT 实现多厂商 Registry / Router 逻辑。`WebSearchService` 作为跨模块调用的 Application 入口，隐藏 Infrastructure 实现细节。

#### Scenario: 正常搜索调用

- **WHEN** 通过 `WebSearchService.search(request)` 发起搜索
- **THEN** 服务 SHALL 委托注入的 `IWebSearchProvider` 执行搜索，返回 `WebSearchResponse`

#### Scenario: 服务记录搜索日志

- **WHEN** 搜索执行完成
- **THEN** 服务 SHALL 记录搜索关键词和返回结果数量的日志

#### Scenario: 服务仅依赖 Port 抽象

- **WHEN** 查看 `WebSearchService` 的构造函数和方法签名
- **THEN** 服务 SHALL 仅依赖 `IWebSearchProvider`（Domain Port），SHALL NOT 直接依赖 `BochaWebSearchAdapter` 或任何 Infrastructure 实现类

---

### Requirement: 搜索配置通过环境变量注入

系统 SHALL 在 `src/shared/config.py` 的 `Settings` 中新增搜索配置字段：
- `BOCHA_API_KEY: str = ""`（博查 API Key，默认空字符串）
- `BOCHA_BASE_URL: str = "https://api.bochaai.com"`（博查 API 基础 URL）

API Key SHALL NOT 硬编码在代码中。`BOCHA_API_KEY` 默认为空字符串，未配置时 SHALL NOT 在应用启动时崩溃，仅在实际调用搜索时检查并抛出 `WebSearchConfigError`。

#### Scenario: 配置从环境变量加载

- **WHEN** 设置环境变量 `BOCHA_API_KEY=xxx` 后启动应用
- **THEN** `settings.BOCHA_API_KEY` SHALL 为 `xxx`

#### Scenario: 未配置 API Key 时应用正常启动

- **WHEN** 未设置 `BOCHA_API_KEY` 环境变量
- **THEN** 应用 SHALL 正常启动，`settings.BOCHA_API_KEY` 为空字符串，不影响 LLM 或其他模块功能

---

### Requirement: Presentation 层 REST 搜索接口

llm_platform 的 Presentation 层 SHALL 新增 `search_routes.py`，定义 `POST /llm-platform/web-search` 接口。请求体为 Pydantic DTO（`query` 必填，`freshness` / `summary` / `count` 可选），响应体为搜索结果。

路由 SHALL 通过 FastAPI `Depends` 链装配 `BochaWebSearchAdapter` → `WebSearchService`（从 `settings` 获取 API Key 和 Base URL）。

异常映射：
- `WebSearchConfigError` → HTTP 503（服务未配置）
- `WebSearchConnectionError` → HTTP 503（上游不可达）
- `WebSearchError` → HTTP 502（上游错误）
- 其他未预期异常 → HTTP 500（记录日志）

#### Scenario: 正常搜索请求返回 200

- **WHEN** 发送 `POST /llm-platform/web-search` 请求，body 包含 `{"query": "A股最新政策"}`
- **THEN** 系统 SHALL 返回 HTTP 200，响应体包含搜索结果列表

#### Scenario: query 缺失时返回 422

- **WHEN** 发送 `POST /llm-platform/web-search` 请求，body 中缺少 `query` 字段
- **THEN** 系统 SHALL 返回 HTTP 422（FastAPI 自动校验），响应体包含字段缺失的错误信息

#### Scenario: API Key 未配置时返回 503

- **WHEN** `BOCHA_API_KEY` 未配置，发送搜索请求
- **THEN** 系统 SHALL 返回 HTTP 503，响应体包含服务未配置的错误信息

#### Scenario: 博查 API 不可用时返回 503

- **WHEN** 博查 API 网络不可达或超时
- **THEN** 系统 SHALL 返回 HTTP 503，响应体包含上游不可达的错误信息

#### Scenario: 博查 API 返回错误时返回 502

- **WHEN** 博查 API 返回 HTTP 4xx/5xx 错误
- **THEN** 系统 SHALL 返回 HTTP 502，响应体包含上游错误信息

---

### Requirement: 下游模块通过 Application 接口消费搜索能力

下游模块（如 Research 的宏观情报员、催化剂侦探）SHALL 仅通过 `llm_platform` 的 **Application 接口**（`WebSearchService`）消费搜索能力，SHALL NOT 直接依赖 `IWebSearchProvider` Port、`BochaWebSearchAdapter` 或任何 Infrastructure 实现。入参/出参 SHALL 使用 Domain 层定义的 DTO（`WebSearchRequest` / `WebSearchResponse`）。

#### Scenario: 跨模块调用走 Application 入口

- **WHEN** Research 模块的某个 Agent 需要网页搜索
- **THEN** 该 Agent 的 Infrastructure Adapter SHALL 通过 `WebSearchService.search(request)` 调用搜索，SHALL NOT 直接实例化 `BochaWebSearchAdapter` 或引用 Infrastructure 层代码

---

### Requirement: 搜索能力不影响现有 LLM 能力

本变更 SHALL NOT 修改现有 LLM 生成相关代码（`ILLMProvider`、`LLMService`、`LLMRegistry`、`LLMRouter`、`OpenAIProvider`、`chat_routes.py`）。搜索能力为独立新增，与文本生成并列。

#### Scenario: LLM 生成功能不受影响

- **WHEN** 部署搜索能力后调用 LLM 文本生成接口
- **THEN** LLM 生成 SHALL 正常工作，行为与变更前完全一致

---

### Requirement: 可测性 — Scenario 与测试一一对应

每个上述 Scenario 在变更交付时 SHALL 对应至少一个自动化测试（单元或集成）；需求完成的验收条件包含「该需求下所有 Scenario 的测试通过」。实现时可采用先实现再补测，不强制测试先行。

#### Scenario: 测试覆盖适配器正常映射

- **WHEN** 运行搜索相关测试套件
- **THEN** 存在测试用例：mock HTTP 响应为正常博查 API 返回，断言适配器正确映射为 `WebSearchResponse`（对应「正常搜索返回映射结果」）

#### Scenario: 测试覆盖适配器错误处理

- **WHEN** 运行搜索相关测试套件
- **THEN** 存在测试用例：mock HTTP 返回 500 → 断言抛出 `WebSearchError`；mock 超时 → 断言抛出 `WebSearchConnectionError`；mock API Key 为空 → 断言抛出 `WebSearchConfigError`

#### Scenario: 测试覆盖搜索服务编排

- **WHEN** 运行搜索相关测试套件
- **THEN** 存在测试用例：mock `IWebSearchProvider` 返回固定响应，断言 `WebSearchService` 正确透传结果

#### Scenario: 测试覆盖配置加载

- **WHEN** 运行搜索相关测试套件
- **THEN** 存在测试用例：验证 `Settings` 中 `BOCHA_API_KEY` 和 `BOCHA_BASE_URL` 的默认值和环境变量覆盖行为
