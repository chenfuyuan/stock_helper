## Context

data_engineering 模块是整个系统的数据底座，负责从 Tushare 接入股票基础信息、日线行情和财务指标数据。当前同步机制有以下现状：

- **四个独立 Job**：`sync_history_daily_data_job`、`sync_daily_data_job`、`sync_finance_history_job`、`sync_incremental_finance_job`，定义在 `presentation/jobs/sync_scheduler.py`。
- **进度管理**：通过 `sync_daily_state.json`、`sync_finance_state.json`、`sync_finance_failures.json` 三个本地 JSON 文件追踪，由 scheduler 层的全局函数读写。
- **限速**：`TushareClient._rate_limited_call()` 用全局 asyncio.Lock + 0.35s 最小间隔实现（≈170 次/分钟，安全低于 200 次限制）。但 `SyncDailyHistoryUseCase` 额外叠加了 `Semaphore(5)` + `sleep(0.1)`，限速策略分散。
- **DI 缺失**：`sync_scheduler.py` 直接 import 并实例化 `StockRepositoryImpl`、`StockDailyRepositoryImpl`、`StockFinanceRepositoryImpl`、`TushareClient`，Presentation 层与 Infrastructure 强耦合。
- **增量同步**：财务增量的"策略 C（失败重试）"仅声明未实现；日线增量按 `trade_date=today` 一次性拉取，无补偿能力。

**约束**：Tushare 接口每分钟 200 次调用上限；数据库为 PostgreSQL（async SQLAlchemy）；调度框架为 APScheduler。

## Goals / Non-Goals

**Goals:**

1. **一次触发、跑完全量**：历史同步 Job 触发后自动分批循环直到完成，中间可断点续跑。
2. **代码结构对齐 Clean Architecture**：Presentation 层通过 DI 获取 Use Case，不直接接触 Infrastructure 实现。
3. **优雅的增量同步**：完善失败重试机制；日线增量支持遗漏检测与自动补偿。
4. **统一限速**：限速逻辑收敛到 Infrastructure 层单一入口，Use Case 零感知。
5. **可靠的状态持久化**：同步进度和失败记录迁移到数据库，取代 JSON 文件。
6. **配置外部化**：批大小、日期范围、限速参数可配置。

**Non-Goals:**

- 不引入分布式任务队列（Celery/RQ 等），仍使用进程内 APScheduler。
- 不重构 `TushareClient` 的 API 方法签名（`fetch_daily`、`fetch_fina_indicator` 等保持不变）。
- 不修改对外暴露的查询接口（`GetDailyBarsForTickerUseCase`、`GetFinanceForTickerUseCase`）。
- 不做数据回填校验（如对比 Tushare 与本地数据一致性）。
- 不修改 `scheduler_routes.py` 的 REST API 路径和响应格式（内部实现替换，接口兼容）。

## Decisions

### Decision 1: 同步状态建模——Domain 实体 + Port

**选择**：在 Domain 层新增 `SyncTask` 实体和 `ISyncTaskRepository` Port，由 Infrastructure 层实现 PostgreSQL 持久化。

```
SyncTask:
  id: UUID
  job_type: SyncJobType (DAILY_HISTORY | FINANCE_HISTORY | DAILY_INCREMENTAL | FINANCE_INCREMENTAL)
  status: SyncTaskStatus (PENDING | RUNNING | COMPLETED | FAILED | PAUSED)
  current_offset: int           # 历史同步当前偏移
  batch_size: int               # 每批处理量
  total_processed: int          # 已处理总数
  started_at: datetime
  updated_at: datetime
  completed_at: datetime | None
  config: dict                  # job 特定配置（start_date、end_date 等）

SyncFailureRecord:
  id: UUID
  job_type: SyncJobType
  third_code: str               # 失败的股票代码
  error_message: str
  retry_count: int
  max_retries: int
  last_attempt_at: datetime
  resolved_at: datetime | None
```

**替代方案**：继续用 JSON 文件但抽象为 Port → 不可靠、不支持并发查询、难以做失败统计。

**理由**：PostgreSQL 提供 ACID 事务保障，与现有技术栈一致，无新依赖；支持按 `job_type` 查询最近任务、统计失败率等运维需求。

### Decision 2: 历史同步编排——Application 层 SyncEngine

**选择**：新增 `SyncEngine` 应用服务，内部循环分批调用已有的 Use Case（`SyncDailyHistoryUseCase`、`SyncFinanceHistoryUseCase`），每批完成后更新 `SyncTask` 进度。

```
SyncEngine.run_history_sync(job_type, config) -> SyncTask:
    1. 查找或创建 SyncTask（如有 PAUSED/FAILED 的同类型任务，则恢复）
    2. while status != COMPLETED:
       a. 从 SyncTask 读取 current_offset
       b. 调用对应 UseCase.execute(offset, batch_size)
       c. 更新 current_offset、total_processed
       d. 如 batch 返回 0 条 → 标记 COMPLETED
       e. 异常 → 记录 SyncFailureRecord，更新 SyncTask 状态
    3. 返回最终 SyncTask
```

**替代方案**：在 Presentation 层的 job 函数里直接写循环（现状）→ Presentation 承担了编排职责，违反分层。

**理由**：编排逻辑属于 Application 层职责；`SyncEngine` 可被多种触发方式复用（REST API 手动触发、APScheduler 定时触发、CLI 脚本触发）。

### Decision 3: 限速策略收敛到 Infrastructure 层

**选择**：保留 `TushareClient._rate_limited_call()` 作为唯一限速入口，移除 `SyncDailyHistoryUseCase` 中的 `Semaphore(5)` 和 `sleep(0.1)`。

**当前限速参数**：`TUSHARE_MIN_INTERVAL = 0.35s`（≈170 次/分钟）。将此参数提取到配置中（`settings.TUSHARE_MIN_INTERVAL`），默认保持 0.35s。

**替代方案**：在 Application 层做并发控制 + Infrastructure 层做单次限速 → 限速逻辑分散，两层耦合，调参困难。

**理由**：限速是外部 API 的基础设施约束，不是业务逻辑。单一入口更易理解、调试和调参。历史同步改为串行分批后无需 Semaphore 并发控制。

### Decision 4: DI 策略——工厂函数

**选择**：新增 `SyncUseCaseFactory`，封装 session 创建和依赖组装，供 Presentation 层调用。

```python
class SyncUseCaseFactory:
    @staticmethod
    async def create_sync_engine() -> AsyncGenerator[SyncEngine, None]:
        async with AsyncSessionLocal() as session:
            stock_repo = StockRepositoryImpl(session)
            daily_repo = StockDailyRepositoryImpl(session)
            finance_repo = StockFinanceRepositoryImpl(session)
            sync_task_repo = SyncTaskRepositoryImpl(session)
            provider = TushareClient()
            engine = SyncEngine(
                stock_repo=stock_repo,
                daily_repo=daily_repo,
                finance_repo=finance_repo,
                sync_task_repo=sync_task_repo,
                provider=provider,
            )
            yield engine
```

**替代方案 A**：引入 `dependency-injector` 库 → 增加外部依赖，当前项目规模不需要。
**替代方案 B**：FastAPI Depends → 仅适用于 REST 路由，不适用于 APScheduler Job。

**理由**：工厂函数简单直接，兼容 REST 路由和 APScheduler 两种触发路径；session 生命周期清晰（context manager）。

### Decision 5: 增量同步——补偿与重试策略

**选择**：

1. **日线增量补偿**：增量同步前查询 DB 中该市场最新交易日期（`max(trade_date)`），与当前日期比较。若存在间隔（>1 天），自动补同步缺失的日期区间，而非仅同步 today。
2. **财务增量完善**：将"策略 C（失败重试）"从 JSON 文件迁移到 `SyncFailureRecord` 表。每次增量同步前先查询未解决的失败记录（`resolved_at IS NULL AND retry_count < max_retries`），优先重试。
3. **统一重试机制**：所有同步失败统一写入 `SyncFailureRecord`，设置 `max_retries=3`（可配置）。超过最大重试次数的记录标记为需人工干预。

**替代方案**：日线补偿用定时全量重跑 → 浪费 API 调用次数，不优雅。

**理由**：补偿机制确保"最终一致"，不依赖外部调度的可靠性；DB 存储失败记录可做统计和告警。

### Decision 6: 配置管理——扩展 shared config

**选择**：在 `src/shared/config.py` 的 `Settings` 中新增同步相关配置项：

```python
# 同步配置
SYNC_DAILY_HISTORY_BATCH_SIZE: int = 50
SYNC_FINANCE_HISTORY_BATCH_SIZE: int = 100
SYNC_FINANCE_HISTORY_START_DATE: str = "20200101"
SYNC_INCREMENTAL_MISSING_LIMIT: int = 300
SYNC_FAILURE_MAX_RETRIES: int = 3
TUSHARE_MIN_INTERVAL: float = 0.35
```

**替代方案**：独立的 sync_config.yaml → 增加维护成本，且当前配置项不多。

**理由**：利用现有 pydantic Settings 机制，支持环境变量覆盖；集中管理，无额外文件。

## Risks / Trade-offs

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| **历史同步长时间运行**：一次触发跑完全量可能需要数小时（约 5000 只股票 × 3 API/股 × 0.35s ≈ 1.5h），期间进程不能崩溃 | 数据不完整 | `SyncTask` 记录 offset，崩溃后重启自动恢复（断点续跑）；日志记录每批进度 |
| **DB migration 风险**：新增 `sync_tasks` 和 `sync_failure_records` 表 | 部署复杂度增加 | Alembic migration 脚本，可回滚；新表独立，不影响现有表 |
| **JSON 文件进度丢弃**：迁移后不再读取旧 JSON 文件 | 若旧进度未跑完需重跑 | 接受一次性重跑代价（历史同步幂等，upsert 不会产生脏数据）；或提供一次性 migration 脚本读取 JSON → 写入 DB |
| **限速参数调优**：移除 Use Case 层的并发控制后，若 TushareClient 限速不准确可能触发封禁 | API 被限流 | 默认 0.35s 已有余量（实际 ≈170 次/分钟 < 200 限制）；可通过配置进一步调低；完善 API 错误处理（检测 429/限流响应并自动 backoff） |
| **长事务风险**：全量同步在单个 session 中跑完所有批次 | DB 连接占用、锁 | 每批独立 session（工厂每批创建新 session），或在 SyncEngine 中按批切分事务边界 |

## Open Questions

1. **是否需要 WebSocket/SSE 推送同步进度**？当前 REST API 可轮询 `SyncTask` 状态，但实时推送体验更好。建议 MVP 阶段用轮询，后续按需加推送。
2. **日线历史同步的起始日期如何确定**？当前按 stock 的 `list_date` 拉全历史；是否需要像财务数据一样设置一个全局 `start_date`（如 `20100101`）？
3. **是否引入同步任务的优先级队列**？当前各 job 独立运行；若同时触发多个 job 是否需要排队以避免突破限速？建议 MVP 阶段同一时间只运行一个同步 job（通过 `SyncTask` 的 RUNNING 状态互斥）。
