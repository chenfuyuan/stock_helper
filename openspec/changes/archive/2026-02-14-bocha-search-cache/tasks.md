## 1. Domain 层定义（Port + DTO）

- [x] 1.1 新增 `WebSearchCacheEntry` DTO（`src/modules/llm_platform/domain/dtos/web_search_cache_entry.py`），包含 `cache_key`、`request_params`、`response_data`、`created_at`、`expires_at` 字段
- [x] 1.2 新增 `IWebSearchCacheRepository` Port（`src/modules/llm_platform/domain/ports/web_search_cache_repository.py`），定义 `get()`、`put()`、`cleanup_expired()` 三个抽象方法
- [x] 1.3 新增缓存键生成函数与 TTL 计算函数（可放在 Domain 层的工具模块或 DTO 旁），实现 SHA-256 哈希和 freshness → TTL 映射

## 2. Infrastructure 层实现（持久化 + Decorator）

- [x] 2.1 新增 Alembic migration：创建 `web_search_cache` 表（`cache_key` VARCHAR(64) PK、`request_params` JSONB、`response_data` TEXT、`created_at` TIMESTAMP、`expires_at` TIMESTAMP + 索引）
- [x] 2.2 新增 ORM Model（`src/modules/llm_platform/infrastructure/persistence/web_search_cache_model.py`），映射 `web_search_cache` 表
- [x] 2.3 新增 `PgWebSearchCacheRepository`（`src/modules/llm_platform/infrastructure/persistence/web_search_cache_repository.py`），实现 `IWebSearchCacheRepository`，包含 UPSERT 写入、过期过滤查询、过期清理
- [x] 2.4 新增 `CachingWebSearchProvider`（`src/modules/llm_platform/infrastructure/adapters/caching_web_search_provider.py`），实现 `IWebSearchProvider`，包装 inner provider + cache repository，执行缓存命中/未命中逻辑，缓存写入失败不阻塞

## 3. Container 装配

- [x] 3.1 修改 `LLMPlatformContainer.web_search_service()`：有 session 时用 `CachingWebSearchProvider` 包装 `BochaWebSearchAdapter`，无 session 时保持原逻辑

## 4. 测试

- [x] 4.1 缓存键生成单元测试：相同请求 → 相同 key、不同参数 → 不同 key、key 为 64 字符十六进制
- [x] 4.2 TTL 计算单元测试：验证各 freshness 值对应的 TTL 正确
- [x] 4.3 `CachingWebSearchProvider` 单元测试：mock cache repo + inner provider，验证缓存命中不调用 inner、缓存未命中调用 inner 并写入、缓存写入失败不阻塞、搜索失败不写缓存
- [x] 4.4 `PgWebSearchCacheRepository` 集成测试：验证写入/读取、过期不返回、UPSERT 覆盖、cleanup_expired 删除过期条目
