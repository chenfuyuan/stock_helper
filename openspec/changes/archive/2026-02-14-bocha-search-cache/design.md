## Context

每次研究任务调用博查 Web Search API 8 次（宏观情报员 4 维度 + 催化剂侦探 4 维度）。其中：

- **全局维度**（2/8）：「货币与流动性」「宏观经济」查询仅含 `{current_year}`，与股票/行业无关，同一天内任何研究任务发出相同请求。
- **行业维度**（2/8）：「产业政策」「行业景气」查询含 `{industry}` + `{current_year}`，同行业股票发出相同请求。
- **个股维度**（4/8）：催化剂侦探 4 个维度查询含 `{stock_name}`，仅同一股票 retry/重复分析时命中。

当前 `WebSearchService` 每次都透传到 `BochaWebSearchAdapter` 发起实际 HTTP 调用。已有 `IWebSearchProvider` Port（ABC）和 `BochaWebSearchAdapter` 实现，`LLMPlatformContainer` 负责装配。

## Goals / Non-Goals

**Goals:**

- 对重复的博查搜索请求命中缓存，避免重复调用，降低 API 配额消耗和响应延迟
- 缓存对所有消费者（Research 模块的 MacroDataAdapter、CatalystDataAdapter 等）完全透明，无需修改任何消费者代码
- 缓存 TTL 按搜索请求的 `freshness` 参数动态计算，时效要求高的维度缓存时间短
- 缓存持久化到 PostgreSQL，进程重启不丢失、多 worker 共享

**Non-Goals:**

- 不实现内存级缓存（如 LRU Cache）—— 本项目为单实例 + 异步，DB 缓存已满足需求
- 不实现主动缓存预热或定时刷新 —— 当前按需缓存即可
- 不实现缓存管理 REST API（如手动清除缓存）—— 可通过 SQL 直接管理
- 不修改 `WebSearchService` 接口或现有 Spec 的行为约束

## Decisions

### Decision 1: Decorator 模式包装 IWebSearchProvider

**选择**：新增 `CachingWebSearchProvider`，实现 `IWebSearchProvider`，包装实际的 `BochaWebSearchAdapter`。在 `search()` 中先查缓存，命中则直接返回 `WebSearchResponse`，未命中则委托给被包装的 provider 调用后写入缓存。

**替代方案**：
- (A) 在 `WebSearchService` 内部加缓存逻辑 → 违反单一职责，且 `WebSearchService` 的 spec 定义为「透传 + 日志」
- (B) 在 Research 模块的 Adapter 层加缓存 → 需要在 MacroDataAdapter 和 CatalystDataAdapter 都加，重复且不覆盖其他潜在消费者

**理由**：Decorator 模式遵循开闭原则，不修改现有类，对 `WebSearchService` 和所有消费者透明。缓存逻辑内聚在一个类中。

### Decision 2: Cache Key 为请求参数的确定性哈希

**选择**：Cache Key = SHA-256(`query` + `freshness` + `summary` + `count`) 的十六进制摘要。这四个字段完全决定了博查 API 的请求体，相同参数必然产生相同响应。

**理由**：
- 使用哈希而非原始 query 作为主键：避免超长 query 导致索引效率低
- SHA-256 碰撞概率可忽略不计
- `freshness` 纳入 key：同一 query 不同 freshness 可能返回不同结果

### Decision 3: TTL 基于 freshness 参数动态计算

**选择**：

| freshness | TTL |
|-----------|-----|
| `oneDay` | 4 小时 |
| `oneWeek` | 12 小时 |
| `oneMonth` | 24 小时 |
| `oneYear` | 48 小时 |
| `noLimit` / `None` | 24 小时 |

**理由**：freshness 反映了调用方对数据时效性的期望。`oneDay` 需要最新数据，缓存时间最短；`oneMonth` 容忍月级时效，24 小时缓存足够。TTL 远小于 freshness 窗口，确保缓存数据在时效窗口内仍然有效。

### Decision 4: PostgreSQL 持久化（非内存缓存）

**选择**：新增 `web_search_cache` 表，列包括 `cache_key`（主键）、`request_params`（JSONB）、`response_data`（TEXT，存 WebSearchResponse 的 JSON 序列化）、`created_at`、`expires_at`。

**替代方案**：
- (A) 内存 dict / LRU Cache → 进程重启丢失、多 worker 不共享
- (B) Redis → 引入新外部依赖，当前项目无 Redis
- (C) 复用 `external_api_call_logs` 表 → 该表是审计日志（只追加），语义不同，且无过期清理机制

**理由**：PostgreSQL 已是项目核心依赖，无需引入新基础设施。数据库缓存天然支持多 worker 共享和持久化。

### Decision 5: 缓存 Repository Port 归属 llm_platform 模块

**选择**：
- Port 定义：`src/modules/llm_platform/domain/ports/web_search_cache_repository.py`（`IWebSearchCacheRepository`，ABC）
- PostgreSQL 实现：`src/modules/llm_platform/infrastructure/persistence/web_search_cache_repository.py`
- ORM Model：`src/modules/llm_platform/infrastructure/persistence/web_search_cache_model.py`
- Decorator：`src/modules/llm_platform/infrastructure/adapters/caching_web_search_provider.py`

**理由**：缓存是 web search 能力的基础设施关注点，归属 `llm_platform` 模块。不放 `src/shared/` 因为它不是跨模块共享的通用能力。

### Decision 6: Container 装配逻辑

**选择**：修改 `LLMPlatformContainer.web_search_service()` 方法，在创建 `BochaWebSearchAdapter` 后，用 `CachingWebSearchProvider` 包装，再注入 `WebSearchService`。当 session 存在时注入缓存 Repository 实现；无 session 时不启用缓存（降级为直接调用）。

```
adapter = BochaWebSearchAdapter(...)
if session:
    cache_repo = PgWebSearchCacheRepository(session)
    adapter = CachingWebSearchProvider(inner=adapter, cache_repo=cache_repo)
service = WebSearchService(provider=adapter, ...)
```

### Decision 7: 过期缓存懒清理

**选择**：查询缓存时通过 `WHERE expires_at > now()` 过滤，过期条目不返回但不立即删除。提供一个独立的 `cleanup_expired()` 方法供定时任务或手动调用。

**理由**：懒清理足够简单，不增加写入时的复杂度。过期数据不影响正确性，定期清理可选。

## Risks / Trade-offs

- **缓存一致性**：博查 API 的实时数据可能在 TTL 内发生变化 → TTL 设置远小于 freshness 窗口，可接受的 trade-off；极端场景下用户可手动清缓存（SQL）
- **数据库负载**：每次搜索增加一次缓存查询 → 按 cache_key 主键查询，O(1) 索引查找，开销远小于博查 HTTP 调用
- **缓存表膨胀**：大量不同 query 可能积累 → `cleanup_expired()` 定期清理；response_data 为 TEXT 但单条数据量有限（博查返回 6-10 条摘要）
- **无 session 时无缓存**：`LLMPlatformContainer` 无 session 时 `CachingWebSearchProvider` 不启用 → REST 直接调用搜索接口不走缓存，但这些场景不是主要调用路径（Research 流水线通过 Container 组装，始终有 session）
