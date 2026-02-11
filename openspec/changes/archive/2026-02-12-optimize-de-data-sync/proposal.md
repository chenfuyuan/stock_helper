## Why

data_engineering 模块当前的数据同步机制存在三个核心痛点：

1. **历史全量同步不可靠**：进度通过本地 JSON 文件（`sync_daily_state.json`、`sync_finance_state.json`）管理，易丢失、不支持分布式部署；批大小和日期范围硬编码，无法灵活调整。每次调度只处理一批（50～100 只股票），需反复触发才能同步完毕，缺少"一次触发、跑完全量"的能力。
2. **代码结构违反 Clean Architecture**：`sync_scheduler.py`（Presentation 层）直接 import 并实例化 `StockRepositoryImpl`、`TushareClient` 等 Infrastructure 类，绕过依赖注入；失败记录逻辑在 scheduler 和 `SyncIncrementalFinanceDataUseCase` 中各写一份，路径和格式不统一。
3. **增量同步不够优雅**：财务增量同步的"策略 C（失败重试）"未完整实现；JSON 文件做失败记录不可靠；日线增量仅按当日日期一次拉取，缺少补偿机制（如遇异常漏同步后无法自动追补）。

此外，Tushare 接口存在 **每分钟 200 次** 的调用频率限制。当前虽有全局限速锁（`_rate_limited_call`），但历史全量同步 Use Case 层额外叠加了 `Semaphore` 和 `sleep`，限速策略分散在多处，维护困难。

## What Changes

- **引入同步引擎（Sync Engine）**：在 Application 层提供统一的同步编排能力，支持"一次触发、自动分批、跑完全量"的历史同步模式，以及"按日/按披露驱动"的增量同步模式。
- **统一限速策略**：将 Tushare API 限速收敛到 Infrastructure 层的单一实现（已有 `_rate_limited_call`），移除 Use Case 层散落的 `Semaphore`/`sleep`，上层无需关心限速细节。
- **进度与失败状态持久化重构**：定义 Domain Port（如 `ISyncStateRepository`），将进度/失败记录从 JSON 文件迁移到数据库（或其他可靠存储），支持断点续跑和失败重试。
- **依赖注入清理**：`sync_scheduler.py` 不再直接实例化 Infrastructure 类，改为通过 DI 容器或工厂获取 Use Case 实例；Presentation 层只负责调度触发，不接触 repo/provider 实现。
- **增量同步补偿**：完善失败重试策略（当前的"策略 C"）；为日线增量同步增加"遗漏检测 + 自动补偿"能力，确保不因单次异常丢失数据。
- **配置外部化**：将硬编码的日期范围（`20200101`）、批大小（`50`/`100`/`300`）、限速参数等提取为可配置项。

## Capabilities

### New Capabilities

- `de-data-sync`: 统一数据同步能力——涵盖同步引擎编排（历史全量 / 增量）、限速策略、进度与失败状态持久化、断点续跑、失败重试、配置外部化，以及 Presentation 层的 DI 清理。

### Modified Capabilities

（无现有 spec 需要修改）

## Impact

- **代码路径**：`src/modules/data_engineering/` 下的 `presentation/jobs/`、`application/commands/`、`domain/ports/`、`infrastructure/persistence/` 均会涉及改动。
- **新增 Domain Ports**：`ISyncStateRepository`（进度/失败持久化）；可能新增 `ISyncJobConfig`（配置抽象）。
- **数据库**：新增同步状态表（sync_state / sync_failures），需 Alembic migration。
- **对外接口不变**：`scheduler_routes.py` 暴露的 REST API 保持兼容，仅内部实现重构；`application/queries/` 对 Research 模块暴露的查询接口不受影响。
- **依赖**：无新增外部依赖；保持现有 `tushare`、`APScheduler`、`SQLAlchemy`、`pydantic` 技术栈。
- **风险**：重构过程中需确保现有同步数据不丢失；需设计 migration 将 JSON 文件进度迁移到 DB（或容忍一次性重跑）。
