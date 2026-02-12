# Design: 集成博查 AI Web Search — 为 Agent 提供联网搜索能力

## Context

`llm_platform` 是系统的「软情报网关」Bounded Context，当前仅提供 LLM 文本生成能力（`ILLMProvider` → `OpenAIProvider` → `LLMService`），包含成熟的 Domain Port 抽象、多厂商 Registry/Router 路由与故障转移机制、以及 REST API。本变更在 `llm_platform` 中**并列**新增 Web Search 能力，供 Research 等下游模块消费。

**博查 AI Web Search API 形态**：
- 端点：`POST https://api.bochaai.com/v1/web-search`
- 认证：`Authorization: Bearer <API_KEY>`
- 请求体：`{ "query": str, "freshness": str?, "summary": bool?, "count": int? }`
- 响应体：`{ "_type": "SearchResponse", "queryContext": {...}, "webPages": { "value": [{ "id", "name", "url", "siteName", "siteIcon", "snippet", "summary", "datePublished" }] } }`

**约束**：
- 模块间调用通过 Application 接口；下游（Research）不直接依赖 `llm_platform` 的 Infrastructure。
- 现有 LLM 生成能力（`ILLMProvider` / `LLMService` / Registry / Router）不受影响。
- 代码路径在 `src/modules/llm_platform/` 下。

**已有资产**：
- `ILLMProvider` Port 模式（Domain 抽象 → Infrastructure 实现 → Application 门面）。
- `OpenAIProvider` 的 `AsyncOpenAI` 异步调用模式。
- `Settings`（`src/shared/config.py`）的 `pydantic_settings.BaseSettings` 环境变量注入模式。
- `chat_routes.py` 的 FastAPI Depends + Pydantic DTO 模式。
- Domain 异常体系（`AppException` → `LLMConnectionError` 等）。

**测试约束**：Spec 中每个 Scenario 在交付时须有对应自动化测试。设计决策须考虑可测性（Port 抽象、DI、DTO 便于 mock）。

## Goals / Non-Goals

**Goals:**

- 在 `llm_platform` 中新增 Web Search 能力，与 LLM 生成能力并列，独立闭环。
- 定义搜索 Port 抽象（`IWebSearchProvider`），使 Application 层和下游模块不绑定具体搜索引擎。
- 实现博查 AI Web Search API 适配器，支持核心搜索参数（query、freshness、summary、count）。
- 通过 Application 层 `WebSearchService` 对外暴露搜索入口，供跨模块调用。
- 提供 HTTP REST 接口用于调试和直接调用。
- 搜索配置（API Key）通过环境变量注入，不硬编码。
- **可测性**：Port 抽象 + 依赖注入 + DTO，便于 mock 验证。

**Non-Goals:**

- 不实现多搜索引擎 Registry / Router（当前仅博查一个提供商，不做过度设计；Port 抽象已为未来扩展预留接口）。
- 不实现搜索结果缓存或持久化。
- 不实现 Research 模块中具体专家（宏观情报员、催化剂侦探）对搜索的消费——那是各自专家的独立变更。
- 不修改现有 LLM 生成能力的任何代码。
- 不实现博查 AI 的 AI Search API / Agent Search API / Semantic Reranker API（本变更仅 Web Search API）。

## Decisions

### 1. 搜索 Port 独立于 LLM Port，不复用 ILLMProvider

- **选择**：在 `domain/ports/` 中新增 `IWebSearchProvider`（ABC），签名为 `async def search(request: WebSearchRequest) -> WebSearchResponse`。该 Port 与 `ILLMProvider` 完全独立，不存在继承关系。
- **备选**：在 `ILLMProvider` 上扩展 `search()` 方法。
- **理由**：搜索与文本生成是完全不同的能力域——输入/输出契约不同、底层 API 不同、计费逻辑不同。强行合并会违反接口隔离原则（ISP），导致所有 LLM Provider 被迫实现搜索方法。独立 Port 保持各自职责清晰，也便于未来独立演进（如更换搜索引擎不影响 LLM）。

### 2. DTO 设计：厂商无关的标准搜索 DTO

- **选择**：Domain 层定义厂商无关的搜索 DTO：

  | DTO | 字段 | 说明 |
  |-----|------|------|
  | `WebSearchRequest` | `query: str`, `freshness: Optional[str]`, `summary: bool = True`, `count: int = 10` | 搜索请求入参。`freshness` 可选值：`oneDay` / `oneWeek` / `oneMonth` / `oneYear` / `noLimit`，默认不限。 |
  | `WebSearchResponse` | `query: str`, `total_matches: Optional[int]`, `results: List[WebSearchResultItem]` | 搜索响应，包含原始查询和结果列表。 |
  | `WebSearchResultItem` | `title: str`, `url: str`, `snippet: str`, `summary: Optional[str]`, `site_name: Optional[str]`, `published_date: Optional[str]` | 单条搜索结果。`summary` 为博查 AI 生成的摘要（当请求 `summary=True` 时有值）。 |

  所有 DTO 使用 Pydantic `BaseModel`，遵循项目 DTO 约定。

- **理由**：厂商无关设计使得 Port 定义的输入/输出不绑定博查 API 的字段命名（如博查的 `webPages.value[].name` 在 DTO 中为 `title`）。未来更换搜索引擎只需新增 Adapter 映射，Application 与下游无感知。

### 3. 博查适配器：异步 HTTP 客户端 + 错误映射

- **选择**：在 `infrastructure/adapters/` 中新增 `BochaWebSearchAdapter`（实现 `IWebSearchProvider`），使用 `httpx.AsyncClient` 调用博查 API。
  - 构造函数接收 `api_key: str` 和 `base_url: str`（默认 `https://api.bochaai.com`）。
  - `search()` 方法将 `WebSearchRequest` 转为博查 API 请求格式，发送 POST 请求，将响应映射为 `WebSearchResponse`。
  - 错误处理：HTTP 4xx/5xx → 记录日志并抛出 `WebSearchError`（新增 Domain 异常）；网络超时/连接失败 → 抛出 `WebSearchConnectionError`。
  - 请求超时默认 30 秒（可配置）。

- **备选**：使用 `aiohttp` 或同步 `requests`。
- **理由**：`httpx` 提供原生 async 支持，API 与 `requests` 类似但异步友好，且已在 Python 生态中广泛采用。项目已使用异步模式（AsyncOpenAI、asyncpg），`httpx.AsyncClient` 是自然选择。`httpx` 作为新依赖需加入 `requirements.txt`（若尚未存在）。

### 4. Application 层：简单门面，不做 Registry/Router

- **选择**：新增 `WebSearchService`（Application 层门面），构造函数注入 `IWebSearchProvider`，暴露 `async def search(request: WebSearchRequest) -> WebSearchResponse` 方法。当前仅做透传 + 日志 + 异常包装，不实现多厂商路由。

- **备选**：参照 LLM 的 `LLMRegistry` + `LLMRouter` 模式实现搜索引擎路由。
- **理由**：当前仅博查一个搜索提供商，Registry/Router 是过度设计。Port 抽象（`IWebSearchProvider`）已为未来多引擎预留扩展点；当真正需要第二个搜索引擎时再引入 Registry/Router，符合 YAGNI 原则。`WebSearchService` 的价值在于：1) 作为跨模块调用的 Application 入口（隐藏 Infrastructure）；2) 统一日志与异常处理。

### 5. 搜索配置：环境变量注入，对齐 Settings 模式

- **选择**：在 `src/shared/config.py` 的 `Settings` 中新增：
  ```python
  BOCHA_API_KEY: str = ""
  BOCHA_BASE_URL: str = "https://api.bochaai.com"
  ```
  博查适配器通过 `settings.BOCHA_API_KEY` / `settings.BOCHA_BASE_URL` 初始化。API Key 缺失或为空时，搜索服务在调用时抛出明确错误（而非启动时崩溃，因为搜索是可选能力）。

- **理由**：对齐已有 `LLM_API_KEY` / `LLM_BASE_URL` 的配置模式；使用 `pydantic_settings` 自动从 `.env` 文件或环境变量加载，部署灵活。默认值为空字符串，未配置时按需报错，不阻塞其他模块启动。

### 6. Domain 异常：新增搜索相关异常

- **选择**：在 `domain/exceptions.py` 中新增：
  - `WebSearchError(AppException)`：通用搜索错误（如 API 返回错误码、响应格式异常）。
  - `WebSearchConnectionError(AppException)`：网络连接 / 超时错误（HTTP 层面失败）。
  - `WebSearchConfigError(AppException)`：配置错误（如 API Key 未配置）。

- **理由**：与 LLM 异常体系（`LLMConnectionError`、`LLMProviderException`）对称；下游可按异常类型做差异化处理（如连接错误可重试，配置错误不可重试）。继承 `AppException` 携带 `code` 和 `status_code`。

### 7. Presentation 层：POST 接口，对齐 chat_routes 模式

- **选择**：在 `presentation/rest/` 中新增 `search_routes.py`，定义：
  - `POST /llm-platform/web-search`：接收 `WebSearchApiRequest`（Pydantic DTO：query 必填，freshness / summary / count 可选），返回 `WebSearchApiResponse`（含结果列表）。
  - 异常映射：`WebSearchConfigError` → 503、`WebSearchConnectionError` → 503、`WebSearchError` → 502、其他 → 500。
  - 依赖注入：通过 `Depends` 链装配 `BochaWebSearchAdapter` → `WebSearchService`。

- **理由**：POST 更适合搜索（请求体可能较大、参数语义非幂等查询）；路由前缀 `/llm-platform/` 与 `chat_routes.py` 的 `/llm-platform/chat/` 同级；异常处理与 `chat_routes.py` 模式一致。

### 8. 目录与分层结构

- **选择**：在 `src/modules/llm_platform/` 已有结构上扩展：

  ```
  src/modules/llm_platform/
  ├── domain/
  │   ├── ports/
  │   │   ├── llm.py              # 已有 ILLMProvider
  │   │   └── web_search.py       # 新增 IWebSearchProvider
  │   ├── dtos/
  │   │   └── web_search_dtos.py  # 新增 WebSearchRequest/Response/ResultItem
  │   └── exceptions.py           # 扩展 WebSearchError 等
  ├── application/
  │   └── services/
  │       ├── llm_service.py      # 已有
  │       └── web_search_service.py  # 新增 WebSearchService
  ├── infrastructure/
  │   └── adapters/
  │       ├── openai.py           # 已有
  │       └── bocha_web_search.py # 新增 BochaWebSearchAdapter
  └── presentation/
      └── rest/
          ├── chat_routes.py      # 已有
          └── search_routes.py    # 新增搜索路由
  ```

  注意：`domain/dtos/` 为新增子目录。若现有 DTO 散落在其他位置，可视情况直接放 `domain/` 下（如 `domain/web_search_dtos.py`），与已有命名风格保持一致。

- **理由**：与已有 LLM 能力的目录模式对称（Port + Adapter + Service + Route 各一个文件）；搜索相关代码内聚在各自文件中，不与 LLM 代码交叉。

### 9. 实现顺序与测试

- **选择**：实现顺序灵活。建议按 Tasks 的依赖排序执行：Domain DTO + Port → 配置 → Infrastructure Adapter → Application Service → Presentation Route → 完整测试。交付前须补全所有 Spec Scenario 的测试。
- **理由**：Domain 先行确保契约清晰；Adapter 依赖 Port；Service 依赖 Adapter；Route 依赖 Service。

## Risks / Trade-offs

| 风险 | 缓解 |
|------|------|
| 博查 API 不可用或限流 | Adapter 设置合理超时（30s）+ 重试（可选 1 次）；Domain 异常区分连接错误与业务错误，便于上层决策（如 Research 可降级跳过搜索）。 |
| 博查 API 响应格式变化（字段重命名/缺失） | Adapter 内做防御性解析（缺失字段给默认值、未知字段忽略）；DTO 的 Optional 字段设默认 None；测试覆盖异常响应场景。 |
| API Key 泄露 | API Key 仅通过环境变量注入，不硬编码；日志中禁止打印 API Key；`.env` 文件在 `.gitignore` 中。 |
| `httpx` 新增依赖 | `httpx` 是成熟稳定的库（Python 生态标准异步 HTTP 客户端）；版本锁定在 `requirements.txt`。若项目已有 `aiohttp`，可改用 `aiohttp`。 |
| 搜索能力未配置时影响其他模块启动 | `BOCHA_API_KEY` 默认空字符串，不在启动时校验；仅在实际调用搜索时检查并抛出 `WebSearchConfigError`，不阻塞 LLM 或其他模块。 |
| 单搜索引擎绑定 | Port 抽象已预留多引擎扩展点（`IWebSearchProvider`）；当需要第二个引擎时引入 Registry/Router，Adapter 互换对 Application 透明。 |

## Migration Plan

- **部署**：新增文件，不修改现有代码。需在部署环境中配置 `BOCHA_API_KEY` 环境变量。`httpx` 需加入 `requirements.txt` 并 `pip install`。
- **回滚**：搜索能力为独立新增，回滚即移除相关文件和配置；不影响 LLM 生成能力或其他模块。
- **数据库**：无 schema 变更。

## Open Questions

- 是否需要对搜索结果做简单的结果缓存（如相同 query + freshness 在短时间内命中缓存）？初步决定不做，后续按需加。
- `httpx` vs `aiohttp`：需确认项目是否已有 HTTP 客户端偏好。若已有 `aiohttp`，可优先复用以减少依赖。初步选 `httpx`。
- 博查 API 的 `freshness` 参数是否需要在 Domain DTO 中做枚举约束，还是允许自由字符串？初步决定用 `Optional[str]`，由 Adapter 做值校验，保持 Port 的通用性。
