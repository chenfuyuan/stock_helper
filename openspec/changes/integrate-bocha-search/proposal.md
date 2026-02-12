# Proposal: 集成博查 AI Web Search — 为 Agent 提供联网搜索能力

## Why

Research 五专家中，**宏观情报员**和**催化剂侦探**需要从互联网获取实时宏观新闻、政策变动、行业动态、公司催化事件等「软情报」来支撑分析。当前系统仅有硬数据采集能力（data_engineering：行情 / 财报）和 LLM 文本生成能力（llm_platform：Chat/Completion），**缺乏联网搜索基础设施**，使得这两位专家无法实现。集成博查 AI（Bocha AI）Web Search API 可填补此空缺，为 Agent 提供可控、可审计、国内合规的网页搜索能力，是 Research 五专家闭环的关键前置依赖。

## What Changes

- **新增 Web Search 领域抽象**：在 `llm_platform` 的 Domain 层新增 Web Search Port（如 `IWebSearchProvider`），定义搜索契约（输入：查询词 + 可选过滤参数；输出：结构化搜索结果列表），使上层模块仅依赖抽象而非具体搜索引擎。
- **新增博查 AI Web Search 适配器**：在 `llm_platform` 的 Infrastructure 层实现 Bocha Web Search API 客户端适配器，调用 `POST https://api.bochaai.com/v1/web-search`，将博查返回的 `SearchResponse`（含 `webPages.value[]`：标题、URL、摘要、summary、发布日期等）映射为 Port 定义的标准 DTO。
- **新增 Application 层搜索服务**：在 `llm_platform` 的 Application 层暴露 `WebSearchService`，作为跨模块调用的入口（Research 等下游通过此 Application 接口消费搜索能力）。
- **搜索配置管理**：博查 API Key 通过环境变量 / 应用配置注入（对齐已有 `settings` 模式），不硬编码在代码中。
- **新增 Presentation 层接口**：提供 HTTP REST 接口（如 `POST /api/v1/llm-platform/web-search`）用于调试和直接调用搜索能力。
- **搜索参数支持**：支持博查 API 的关键参数 — `query`（查询词）、`freshness`（时效过滤：oneDay / oneWeek / oneMonth / oneYear / noLimit）、`summary`（是否生成 AI 摘要）、`count`（返回条数）。

## Capabilities

### New Capabilities

- **`llm-web-search`**：llm_platform 模块的 Web 搜索网关能力。定义搜索抽象（Port）与标准输入/输出 DTO、博查 AI 适配器实现、Application 搜索服务入口、配置管理、HTTP 调试接口、异常处理与日志约定。该能力为**供给侧基础设施**，不直接绑定特定 Research 专家——下游模块（如 Research 的宏观情报员、催化剂侦探）各自通过自身 Domain Port 消费此 Application 接口。

### Modified Capabilities

- （无。现有 LLM 生成能力的 `ILLMProvider` / `LLMService` 不受影响；搜索为独立新增能力，与文本生成并列。）

## Impact

- **代码**：在 `src/modules/llm_platform/` 下新增 Domain Port（`IWebSearchProvider`）、搜索结果 DTO（`WebSearchResultDTO`）、Application 服务（`WebSearchService`）、Infrastructure 适配器（`BochaWebSearchAdapter`）、Presentation 路由。不修改现有 LLM 生成相关代码。
- **依赖**：新增外部依赖 — 博查 AI Web Search API（`https://api.bochaai.com/v1/web-search`，需 API Key）。HTTP 客户端可复用已有 `httpx` / `aiohttp` 或标准库 `requests`（视异步需求选择）。
- **配置**：新增博查 API Key 配置项（环境变量 `BOCHA_API_KEY` 或对应 settings 字段），需在部署环境中配置。
- **API/系统**：新增 HTTP 搜索接口（Presentation 层），供调试与直接使用。Research 模块的后续变更（宏观情报员、催化剂侦探）将通过 llm_platform 的 Application 接口消费搜索能力。
- **架构一致性**：搜索能力归属 `llm_platform`（「软情报网关」），与 LLM 生成并列；Research 仅通过 Application 接口消费，不直接依赖 Infrastructure 实现，符合 Context Map 约定。
- **测试与可验证性**：Spec 中所有 Scenario 在交付时须有对应自动化测试；交付以「完整测试通过 + 无跨模块直接依赖」为验收条件。
