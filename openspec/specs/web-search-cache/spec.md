# Spec: web-search-cache

博查搜索结果的数据库缓存能力：通过 Decorator 模式在 `IWebSearchProvider` 层透明缓存搜索结果到 PostgreSQL，按请求参数哈希作为缓存键，按 `freshness` 参数动态设置 TTL，对所有消费者（Research 模块等）完全透明。缓存命中时直接返回，未命中时调用实际搜索并写入缓存。

**测试约定**：每个 `#### Scenario:` 在变更**交付时**须对应至少一个自动化测试用例（单元或集成）；实现顺序可先实现再补测，以完整测试通过为需求完成标准。

---

## ADDED Requirements

### Requirement: 缓存 Repository Port 定义

llm_platform 的 Domain 层 SHALL 新增 `IWebSearchCacheRepository`（ABC），定义搜索结果缓存的持久化契约。该 Port SHALL 包含以下方法：

- `async def get(self, cache_key: str) -> WebSearchCacheEntry | None`：按缓存键查询未过期的缓存条目，过期或不存在返回 None。
- `async def put(self, entry: WebSearchCacheEntry) -> None`：写入或覆盖缓存条目。
- `async def cleanup_expired(self) -> int`：清理已过期的缓存条目，返回删除条数。

#### Scenario: Port 定义完整

- **WHEN** 查看 `IWebSearchCacheRepository` 的方法签名
- **THEN** SHALL 包含 `get(cache_key) -> WebSearchCacheEntry | None`、`put(entry) -> None`、`cleanup_expired() -> int` 三个抽象方法

#### Scenario: Port 位于 Domain 层

- **WHEN** 查看 `IWebSearchCacheRepository` 的模块位置
- **THEN** SHALL 位于 `src/modules/llm_platform/domain/ports/` 下，且仅依赖 Domain 层的 DTO，不依赖任何 Infrastructure 实现

---

### Requirement: 缓存条目 DTO

llm_platform 的 Domain 层 SHALL 新增 `WebSearchCacheEntry`（Pydantic BaseModel），包含以下字段：

- `cache_key: str`（请求参数的 SHA-256 哈希，主键）
- `request_params: dict`（原始请求参数，便于调试）
- `response_data: str`（`WebSearchResponse` 的 JSON 序列化）
- `created_at: datetime`（缓存写入时间）
- `expires_at: datetime`（缓存过期时间）

#### Scenario: DTO 包含完整字段

- **WHEN** 构造 `WebSearchCacheEntry`
- **THEN** SHALL 包含 `cache_key`（str）、`request_params`（dict）、`response_data`（str）、`created_at`（datetime）、`expires_at`（datetime）字段

#### Scenario: DTO 为 Pydantic BaseModel

- **WHEN** 查看 `WebSearchCacheEntry` 的定义
- **THEN** SHALL 继承 `pydantic.BaseModel`，位于 `src/modules/llm_platform/domain/dtos/` 下

---

### Requirement: 缓存键生成规则

系统 SHALL 基于 `WebSearchRequest` 的四个字段（`query`、`freshness`、`summary`、`count`）生成确定性缓存键。缓存键 SHALL 为这四个字段拼接后的 SHA-256 十六进制摘要。相同请求参数 SHALL 始终生成相同的缓存键。

#### Scenario: 相同请求生成相同缓存键

- **WHEN** 两次构造参数完全相同的 `WebSearchRequest`（query、freshness、summary、count 均相同）
- **THEN** 生成的缓存键 SHALL 完全相同

#### Scenario: 不同参数生成不同缓存键

- **WHEN** 两次构造 `WebSearchRequest`，仅 `freshness` 不同（如 `oneWeek` vs `oneMonth`）
- **THEN** 生成的缓存键 SHALL 不同

#### Scenario: 缓存键为 SHA-256 十六进制

- **WHEN** 对任意 `WebSearchRequest` 生成缓存键
- **THEN** 缓存键 SHALL 为 64 字符的十六进制字符串（SHA-256 摘要）

---

### Requirement: TTL 基于 freshness 动态计算

系统 SHALL 根据搜索请求的 `freshness` 参数动态计算缓存 TTL：

| freshness | TTL |
|-----------|-----|
| `oneDay` | 4 小时 |
| `oneWeek` | 12 小时 |
| `oneMonth` | 24 小时 |
| `oneYear` | 48 小时 |
| `noLimit` 或 `None` | 24 小时 |

#### Scenario: oneDay freshness 的 TTL

- **WHEN** 缓存一条 `freshness=oneDay` 的搜索结果
- **THEN** 缓存条目的 `expires_at` SHALL 为 `created_at` + 4 小时

#### Scenario: oneWeek freshness 的 TTL

- **WHEN** 缓存一条 `freshness=oneWeek` 的搜索结果
- **THEN** 缓存条目的 `expires_at` SHALL 为 `created_at` + 12 小时

#### Scenario: oneMonth freshness 的 TTL

- **WHEN** 缓存一条 `freshness=oneMonth` 的搜索结果
- **THEN** 缓存条目的 `expires_at` SHALL 为 `created_at` + 24 小时

#### Scenario: None freshness 使用默认 TTL

- **WHEN** 缓存一条 `freshness=None` 的搜索结果
- **THEN** 缓存条目的 `expires_at` SHALL 为 `created_at` + 24 小时

---

### Requirement: CachingWebSearchProvider Decorator

llm_platform 的 Infrastructure 层 SHALL 新增 `CachingWebSearchProvider`，实现 `IWebSearchProvider` 接口，通过构造函数注入被包装的 `IWebSearchProvider`（如 `BochaWebSearchAdapter`）和 `IWebSearchCacheRepository`。

`search()` 方法的执行流程 SHALL 为：
1. 根据 `WebSearchRequest` 生成缓存键
2. 通过 `IWebSearchCacheRepository.get(cache_key)` 查询缓存
3. 若命中（返回非 None 且未过期），反序列化 `response_data` 为 `WebSearchResponse` 并返回，记录 INFO 级别缓存命中日志
4. 若未命中，委托给被包装的 provider 执行搜索，将结果序列化后通过 `IWebSearchCacheRepository.put()` 写入缓存，记录 INFO 级别缓存未命中日志
5. 缓存写入失败 SHALL NOT 阻塞搜索结果返回，仅记录 WARNING 级别日志

#### Scenario: 缓存命中时不调用实际搜索

- **WHEN** 缓存中存在匹配且未过期的搜索结果
- **THEN** `CachingWebSearchProvider` SHALL 直接返回缓存的 `WebSearchResponse`，SHALL NOT 调用被包装的 `IWebSearchProvider.search()`

#### Scenario: 缓存未命中时调用实际搜索并写入缓存

- **WHEN** 缓存中不存在匹配的搜索结果（或已过期）
- **THEN** `CachingWebSearchProvider` SHALL 委托被包装的 provider 执行搜索，搜索完成后将结果写入缓存，并返回搜索结果

#### Scenario: 缓存写入失败不阻塞返回

- **WHEN** 搜索成功但缓存写入失败（如数据库异常）
- **THEN** 搜索结果 SHALL 正常返回给调用方，系统 SHALL 记录 WARNING 级别日志，SHALL NOT 抛出异常

#### Scenario: 搜索失败时不写入缓存

- **WHEN** 被包装的 provider 搜索失败（抛出异常）
- **THEN** `CachingWebSearchProvider` SHALL 将异常原样抛出，SHALL NOT 将错误结果写入缓存

#### Scenario: 缓存命中记录日志

- **WHEN** 搜索请求命中缓存
- **THEN** 系统 SHALL 记录 INFO 级别日志，包含查询词和缓存键信息

#### Scenario: 缓存未命中记录日志

- **WHEN** 搜索请求未命中缓存
- **THEN** 系统 SHALL 记录 INFO 级别日志，包含查询词信息

---

### Requirement: PostgreSQL 缓存持久化实现

系统 SHALL 新增 `web_search_cache` 数据库表（通过 Alembic migration），包含以下列：

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `cache_key` | `VARCHAR(64)` | PRIMARY KEY | SHA-256 哈希 |
| `request_params` | `JSONB` | NOT NULL | 原始请求参数 |
| `response_data` | `TEXT` | NOT NULL | WebSearchResponse JSON |
| `created_at` | `TIMESTAMP` | NOT NULL | 写入时间 |
| `expires_at` | `TIMESTAMP` | NOT NULL | 过期时间 |

系统 SHALL 在 `expires_at` 列上创建索引，用于加速过期清理查询。

`PgWebSearchCacheRepository` SHALL 实现 `IWebSearchCacheRepository`：
- `get()`：查询 `cache_key` 匹配且 `expires_at > now()` 的记录
- `put()`：使用 UPSERT（INSERT ... ON CONFLICT UPDATE）写入或覆盖缓存
- `cleanup_expired()`：删除 `expires_at <= now()` 的记录

#### Scenario: 缓存写入与读取

- **WHEN** 通过 `put()` 写入一条缓存条目，然后在 TTL 内通过 `get()` 查询相同 `cache_key`
- **THEN** `get()` SHALL 返回之前写入的 `WebSearchCacheEntry`

#### Scenario: 过期缓存不返回

- **WHEN** 缓存条目已过期（`expires_at` 早于当前时间）
- **THEN** `get()` SHALL 返回 `None`

#### Scenario: UPSERT 覆盖已有缓存

- **WHEN** 对已存在的 `cache_key` 再次 `put()` 新的缓存条目
- **THEN** 新条目 SHALL 覆盖旧条目的 `response_data`、`created_at`、`expires_at`

#### Scenario: 清理过期条目

- **WHEN** 调用 `cleanup_expired()`，且存在 N 条已过期的缓存记录
- **THEN** 这些记录 SHALL 被删除，方法返回值为 N

#### Scenario: Alembic migration 可正常执行

- **WHEN** 执行 Alembic upgrade
- **THEN** `web_search_cache` 表 SHALL 被创建，包含上述列定义和索引

---

### Requirement: Container 装配透明集成

`LLMPlatformContainer.web_search_service()` SHALL 在构造 `BochaWebSearchAdapter` 后，当 session 存在时，用 `CachingWebSearchProvider` 包装 adapter 再注入 `WebSearchService`。无 session 时 SHALL 跳过缓存包装，直接使用原始 adapter（降级为无缓存模式）。

#### Scenario: 有 session 时启用缓存

- **WHEN** `LLMPlatformContainer` 构造时传入了 `session`
- **THEN** `web_search_service()` 返回的 `WebSearchService` 内部使用的 provider SHALL 为 `CachingWebSearchProvider`（包装 `BochaWebSearchAdapter`）

#### Scenario: 无 session 时降级为无缓存

- **WHEN** `LLMPlatformContainer` 构造时未传入 `session`（session 为 None）
- **THEN** `web_search_service()` 返回的 `WebSearchService` 内部使用的 provider SHALL 直接为 `BochaWebSearchAdapter`，不包含缓存层

#### Scenario: 消费者代码无需修改

- **WHEN** Research 模块的 `MacroDataAdapter` 和 `CatalystDataAdapter` 通过 `WebSearchService.search()` 发起搜索
- **THEN** 搜索行为 SHALL 与之前一致（命中缓存时更快返回），消费者代码 SHALL NOT 需要任何修改

---

### Requirement: 可测性 — Scenario 与测试一一对应

每个上述 Scenario 在变更交付时 SHALL 对应至少一个自动化测试（单元或集成）；需求完成的验收条件包含「该需求下所有 Scenario 的测试通过」。实现时可采用先实现再补测，不强制测试先行。

#### Scenario: 测试覆盖缓存键生成

- **WHEN** 运行缓存相关测试套件
- **THEN** 存在测试用例：验证相同请求生成相同缓存键、不同请求生成不同缓存键、缓存键格式为 64 字符十六进制

#### Scenario: 测试覆盖 TTL 计算

- **WHEN** 运行缓存相关测试套件
- **THEN** 存在测试用例：验证各 freshness 值对应的 TTL 计算正确

#### Scenario: 测试覆盖 Decorator 缓存命中与未命中

- **WHEN** 运行缓存相关测试套件
- **THEN** 存在测试用例：mock cache repository 返回缓存命中 → 断言不调用 inner provider；mock 返回 None → 断言调用 inner provider 并写入缓存

#### Scenario: 测试覆盖缓存写入失败降级

- **WHEN** 运行缓存相关测试套件
- **THEN** 存在测试用例：mock cache repository 的 put() 抛出异常，断言搜索结果正常返回且不抛出异常
