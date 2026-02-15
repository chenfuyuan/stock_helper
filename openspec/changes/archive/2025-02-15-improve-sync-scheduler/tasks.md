## 1. 数据库 Schema 与 Migration

- [x] 1.1 创建 Alembic migration：新增 `scheduler_job_config` 表（id, job_id, job_name, cron_expression, timezone, enabled, job_kwargs, created_at, updated_at, last_run_at），`job_id` 设唯一约束
- [x] 1.2 创建 Alembic migration：新增 `scheduler_execution_log` 表（id, job_id, started_at, finished_at, status, error_message, duration_ms），`job_id + started_at` 建联合索引
- [x] 1.3 在 migration 中 seed 4 条默认调度配置（sync_daily_by_date 18:00、sync_incremental_finance 00:00、sync_concept_data 18:30、sync_stock_basic 19:00），使用 `INSERT ... ON CONFLICT DO NOTHING` 保证幂等

## 2. 调度持久化 — 模型与 Repository

- [x] 2.1 创建 `src/shared/infrastructure/scheduler/` 包结构（`__init__.py`、`models/`、`repositories/`）
- [x] 2.2 实现 `SchedulerJobConfigModel`（SQLAlchemy ORM）在 `models/scheduler_job_config_model.py`
- [x] 2.3 实现 `SchedulerExecutionLogModel`（SQLAlchemy ORM）在 `models/scheduler_execution_log_model.py`
- [x] 2.4 实现 `SchedulerJobConfigRepository`（`get_all_enabled()`、`get_by_job_id()`、`upsert()`）在 `repositories/scheduler_job_config_repo.py`
- [x] 2.5 实现 `SchedulerExecutionLogRepository`（`create()`、`update()`、`get_recent_by_job_id()`）在 `repositories/scheduler_execution_log_repo.py`

## 3. 调度持久化 — ExecutionTracker

- [x] 3.1 实现 `ExecutionTracker` 异步上下文管理器在 `src/shared/infrastructure/scheduler/execution_tracker.py`：进入时创建 RUNNING 日志记录，正常退出更新为 SUCCESS + duration_ms，异常退出更新为 FAILED + error_message
- [x] 3.2 `ExecutionTracker` 自身的 DB 写入用 `try/except` 保护，失败仅记 ERROR 日志不中断 job

## 4. 调度持久化 — SchedulerService 扩展

- [x] 4.1 将 `src/shared/infrastructure/scheduler.py` 迁移到 `src/shared/infrastructure/scheduler/scheduler_service.py`，更新所有 import
- [x] 4.2 在 `SchedulerService` 中新增 `load_persisted_jobs(registry: Dict[str, Callable], session_factory)` 方法：从 DB 加载 `enabled=True` 的配置，匹配 registry 中的函数，注册到 APScheduler
- [x] 4.3 `load_persisted_jobs` 整体用 `try/except` 包裹，DB 不可用时记 ERROR 日志但不阻止启动
- [x] 4.4 修改 `src/main.py` lifespan：在 `SchedulerService.start()` 后调用 `load_persisted_jobs()`，传入 JOB_REGISTRY

## 5. 调度持久化 — HTTP API 同步持久化

- [x] 5.1 修改 `scheduler_routes.py` 中 `start_job`（interval 模式）：操作 APScheduler 后，upsert DB 中对应的 `SchedulerJobConfig`
- [x] 5.2 修改 `scheduler_routes.py` 中 `schedule_job`（cron 模式）：操作 APScheduler 后，upsert DB 中对应的 `SchedulerJobConfig`
- [x] 5.3 修改 `scheduler_routes.py` 中 `stop_job`：移除 APScheduler job 后，将 DB 中对应配置的 `enabled` 设为 `False`
- [x] 5.4 新增 `GET /scheduler/executions` 端点：按 `job_id` 筛选、`limit` 分页、按 `started_at` 降序返回执行历史

## 6. 调度持久化 — Job 函数集成 ExecutionTracker

- [x] 6.1 修改 `sync_scheduler.py` 中所有 job 函数（sync_history_daily_data_job、sync_daily_data_job、sync_finance_history_job、sync_incremental_finance_job、sync_concept_data_job），在函数内部包裹 `async with ExecutionTracker(...)` 记录执行日志
- [x] 6.2 新增 `sync_stock_basic_job` 函数（股票基础信息同步），并注册到 `JOB_REGISTRY`

## 7. TuShare 滑动窗口限速器

- [x] 7.1 在 `DataEngineeringConfig` 中新增配置项：`TUSHARE_RATE_LIMIT_MAX_CALLS`（默认 195）、`TUSHARE_RATE_LIMIT_WINDOW_SECONDS`（默认 60）；移除旧的 `TUSHARE_MIN_INTERVAL`
- [x] 7.2 实现 `SlidingWindowRateLimiter` 类（`collections.deque` + `asyncio.Lock`），提供 `async def acquire()` 方法：维护时间戳队列，窗口内达到上限时 sleep 等待
- [x] 7.3 替换 `TushareClient._rate_limited_call()` 中的固定间隔逻辑为 `SlidingWindowRateLimiter.acquire()`，移除全局 `_tushare_rate_lock` 和 `_tushare_last_call`

## 8. TuShare 频率超限异常退避重试

- [x] 8.1 在 `_rate_limited_call()` 中增加频率超限异常捕获逻辑：匹配异常消息中的"频率"、"每分钟"等关键词
- [x] 8.2 实现指数退避重试：base=3s、factor=2、max_retries=3，每次重试记录 WARNING 日志
- [x] 8.3 超过最大重试次数后抛出原始异常，非频率超限异常不触发重试

## 9. 僵死任务超时检测

- [x] 9.1 在 `DataEngineeringConfig` 中新增 `SYNC_TASK_STALE_TIMEOUT_MINUTES`（默认 10）
- [x] 9.2 修改 `SyncEngine.run_history_sync` 中互斥检查逻辑：RUNNING 任务的 `updated_at` 超过阈值时，标记为 FAILED（记录超时原因），允许创建新任务
- [x] 9.3 确认 `SyncTask.update_progress()`、`SyncTask.start()` 等所有状态变更方法都正确更新 `updated_at`，确保写入 DB 的路径完整覆盖

## 10. 测试

- [x] 10.1 单元测试：`SlidingWindowRateLimiter` — 窗口内正常调用、达到上限等待、突发友好
- [x] 10.2 单元测试：`ExecutionTracker` — 正常执行记录 SUCCESS、异常记录 FAILED、DB 写入失败不中断
- [x] 10.3 单元测试：`SyncEngine` 僵死任务检测 — 超时标记 FAILED、未超时拒绝、阈值可配置
- [x] 10.4 单元测试：TuShare 频率超限退避重试 — 首次重试成功、多次重试成功、超限后抛出、非频率异常不重试
- [x] 10.5 集成测试：`SchedulerService.load_persisted_jobs()` — 从 DB 加载配置并注册、DB 不可用退化
- [x] 10.6 集成测试：调度 HTTP API 持久化 — schedule/stop 操作同步写入 DB，重启后配置保留
