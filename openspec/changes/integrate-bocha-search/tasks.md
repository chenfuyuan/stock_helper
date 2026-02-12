# Tasks: integrate-bocha-search

集成博查 AI Web Search，为 `llm_platform` 新增 Web 搜索网关能力。任务按依赖排序；实现顺序灵活，交付前须完成完整测试，使所有 Spec Scenario 有对应通过测试。

---

## 1. Domain 层 — 异常定义

- [x] 1.1 在 `domain/exceptions.py` 中新增三个搜索异常类（继承 `AppException`）：`WebSearchError`（通用搜索错误）、`WebSearchConnectionError`（网络连接/超时）、`WebSearchConfigError`（配置缺失，如 API Key 未设置）

## 2. Domain 层 — 搜索 DTO

- [x] 2.1 新增 `domain/web_search_dtos.py`（与已有 `entities/` 同级），定义三个 Pydantic `BaseModel` DTO：`WebSearchRequest`（query: str, freshness: Optional[str], summary: bool = True, count: int = 10）、`WebSearchResponse`（query: str, total_matches: Optional[int], results: List[WebSearchResultItem]）、`WebSearchResultItem`（title: str, url: str, snippet: str, summary: Optional[str], site_name: Optional[str], published_date: Optional[str]）

## 3. Domain 层 — 搜索 Port

- [x] 3.1 新增 `domain/ports/web_search.py`，定义 `IWebSearchProvider`（ABC），含 `async def search(self, request: WebSearchRequest) -> WebSearchResponse` 方法；与 `ILLMProvider` 完全独立，无继承关系

## 4. 配置管理

- [x] 4.1 在 `src/shared/config.py` 的 `Settings` 中新增 `BOCHA_API_KEY: str = ""` 和 `BOCHA_BASE_URL: str = "https://api.bochaai.com"` 两个配置字段

## 5. Infrastructure 层 — 博查适配器

- [x] 5.1 新增 `infrastructure/adapters/bocha_web_search.py`，实现 `BochaWebSearchAdapter`（实现 `IWebSearchProvider`）；构造函数接收 `api_key: str` 和 `base_url: str`；使用 `httpx.AsyncClient` 发送 `POST /v1/web-search` 请求，超时 30 秒
- [x] 5.2 实现请求构建：将 `WebSearchRequest` 的 query / freshness / summary / count 映射为博查 API 请求体
- [x] 5.3 实现响应映射：博查 `webPages.value[]` 中 `name` → `title`、`url` → `url`、`snippet` → `snippet`、`summary` → `summary`、`siteName` → `site_name`、`datePublished` → `published_date`；无结果时返回空列表
- [x] 5.4 实现错误处理：调用前检查 `api_key` 非空（空则抛 `WebSearchConfigError`）；HTTP 4xx/5xx → `WebSearchError`（含状态码信息）；网络超时/连接失败 → `WebSearchConnectionError`；响应 JSON 缺失预期字段时防御性处理（给默认值）

## 6. Application 层 — 搜索服务

- [x] 6.1 新增 `application/services/web_search_service.py`，定义 `WebSearchService`，构造函数注入 `IWebSearchProvider`；暴露 `async def search(self, request: WebSearchRequest) -> WebSearchResponse`，内部委托 Provider 执行搜索
- [x] 6.2 在服务中添加日志记录：搜索前记录 query 关键词，搜索后记录返回结果数量

## 7. Presentation 层 — REST 搜索路由

- [x] 7.1 新增 `presentation/rest/search_routes.py`，定义 Pydantic 请求/响应 DTO（`WebSearchApiRequest`：query 必填 + freshness/summary/count 可选；`WebSearchApiResponse`：含结果列表），创建 `APIRouter`（prefix=`/llm-platform/web-search`）
- [x] 7.2 实现 `POST /` 路由函数：通过 FastAPI `Depends` 装配 `BochaWebSearchAdapter`（从 settings 取 api_key / base_url）→ `WebSearchService`；调用 `service.search()` 返回结果
- [x] 7.3 实现异常映射：`WebSearchConfigError` → 503、`WebSearchConnectionError` → 503、`WebSearchError` → 502、其他 → 500（记录日志）
- [x] 7.4 在 `src/api/routes.py` 中注册新路由：`api_router.include_router(search_routes.router)`

## 8. 完整测试与验收

- [x] 8.1 适配器单元测试：mock `httpx` 响应，验证正常映射（博查字段 → DTO）、空结果返回空列表、请求参数正确传递
- [x] 8.2 适配器错误处理测试：mock HTTP 500 → 断言 `WebSearchError`；mock 超时 → 断言 `WebSearchConnectionError`；api_key 为空 → 断言 `WebSearchConfigError`；响应缺少 `webPages` 字段 → 防御性处理不崩溃
- [x] 8.3 搜索服务测试：mock `IWebSearchProvider` 返回固定响应，断言 `WebSearchService` 正确透传结果
- [x] 8.4 配置测试：验证 `Settings` 中 `BOCHA_API_KEY` / `BOCHA_BASE_URL` 默认值和环境变量覆盖行为
- [x] 8.5 端到端路由测试：使用 FastAPI `TestClient`，mock Provider，验证 200 正常返回、422 query 缺失、503 配置缺失、503 连接失败、502 上游错误
