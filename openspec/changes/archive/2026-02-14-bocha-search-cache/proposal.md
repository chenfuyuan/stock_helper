## Why

每次研究任务需调用博查 Web Search API **8 次**（宏观情报员 4 维度 + 催化剂侦探 4 维度）。其中宏观情报员的「货币与流动性」和「宏观经济」两个维度的查询**完全不含股票/行业参数**（仅依赖当前年份），同一天内分析任何股票都会发送完全相同的请求；「产业政策」和「行业景气」两个维度仅依赖行业，同行业股票查询相同。这些重复调用浪费 API 配额与响应时间，且博查 API 按调用次数计费。

通过引入基于 PostgreSQL 的搜索结果缓存，可在不改变任何消费者代码的前提下，显著减少重复调用。

## What Changes

- 新增 `CachingWebSearchProvider`（Decorator），实现 `IWebSearchProvider`，包装实际的 `BochaWebSearchAdapter`，在调用博查前先查缓存、命中则直接返回、未命中则调用后写入缓存
- 新增 PostgreSQL 缓存表（`web_search_cache`），存储查询参数哈希 → 搜索结果 + 过期时间
- 新增缓存 Repository Port（`IWebSearchCacheRepository`）与 PostgreSQL 实现
- TTL 策略基于搜索请求的 `freshness` 参数动态计算：时效要求越高，缓存时间越短
- 修改 `LLMPlatformContainer` 的 `web_search_service()` 方法，将 `BochaWebSearchAdapter` 包装进 `CachingWebSearchProvider` 后注入 `WebSearchService`
- 新增 Alembic migration 创建缓存表

## Capabilities

### New Capabilities
- `web-search-cache`: 博查搜索结果的数据库缓存能力——包括缓存 Port 定义、PostgreSQL 持久化实现、基于 Decorator 模式的透明缓存层、按 freshness 动态 TTL 策略

### Modified Capabilities
（无需修改现有 spec 的需求级行为。缓存层通过 Decorator 包装 `IWebSearchProvider`，`WebSearchService` 仍做透传，对消费者完全透明。）

## Impact

- **代码**：`src/modules/llm_platform/` 新增缓存相关的 domain port、infrastructure adapter 和 persistence；`LLMPlatformContainer` 装配逻辑微调
- **数据库**：新增 `web_search_cache` 表（Alembic migration）
- **依赖**：无新外部依赖（使用现有 SQLAlchemy + asyncpg）
- **消费者**：`WebSearchService` 接口不变，Research 模块的 `MacroDataAdapter` / `CatalystDataAdapter` 无需任何修改
- **API**：无 REST API 变更
