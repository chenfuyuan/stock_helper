## Why

当前数据同步调度器存在三个运维痛点，严重影响日常使用体验和数据时效性：

1. **调度器配置不持久**：每次应用重启后，所有定时任务丢失，必须手动通过 HTTP 请求重新设置调度计划，无法实现"部署即运行"。
2. **调用效率未最大化**：TuShare API 限制为 200 次/分钟，当前固定间隔策略（0.35s，约 171 次/分钟）未充分利用配额；且缺乏对 TuShare 返回"调用频率过高"异常的优雅处理。
3. **僵死任务阻塞新任务**：同步任务因进程崩溃或未捕获异常而停止时，`SyncTask.status` 卡在 RUNNING，导致互斥检查永远拒绝新任务，只能手动去数据库修复。

这些问题在数据量增大和调度频率提高后愈发突出，需在概念图谱 MVP 上线前解决，避免新增的概念数据同步也继承这些缺陷。

## What Changes

### 调度器配置持久化与自动注册
- **新增** 调度配置表（`scheduler_job_config`），存储每个定时任务的 cron 表达式、启用状态、任务参数等
- **新增** 调度执行记录表（`scheduler_execution_log`），记录每次调度执行的开始时间、结束时间、执行结果、错误信息
- **新增** 应用启动时自动加载已启用的调度配置并注册到 APScheduler
- **新增** 预置以下默认调度计划（北京时间 UTC+8）：
  - 历史日线数据增量同步：每天 18:00
  - 历史财务数据增量同步：每天 00:00
  - 概念数据同步：每天 18:30
  - 股票基础信息同步：每天 19:00
- **保留** 现有 HTTP API 手动管理能力（启动/停止/触发），但操作同时持久化到数据库

### TuShare 调用效率优化
- **替换** 固定间隔限速器（`_rate_limited_call` 中的 `asyncio.Lock + sleep`）为**滑动窗口限速器**（Sliding Window Rate Limiter），在 60 秒窗口内允许接近 200 次请求，提升批量同步场景的吞吐量
- **新增** TuShare 频率超限异常处理：当 API 返回"调用频率过高"错误时，自动退避等待后重试（指数退避，最多 3 次），而非直接抛出异常中断同步

### 僵死任务自动恢复
- **新增** 过期任务检测：在 `SyncEngine.run_history_sync` 的互斥检查中，增加基于 `updated_at` 的超时判断——若 RUNNING 任务的 `updated_at` 距今超过可配置阈值（默认 10 分钟），自动标记为 FAILED 并允许启动新任务
- **强化** 进度更新时效性：确保每批数据同步完成后立即更新 `SyncTask.updated_at`（当前已有此逻辑，需确认所有路径都覆盖）

## Capabilities

### New Capabilities
- `scheduler-persistence`: 调度器配置的数据库持久化、应用启动自动注册、调度执行历史记录与查询

### Modified Capabilities
- `de-data-sync`: 新增僵死任务（stale RUNNING）超时检测与自动恢复机制；将 TuShare 固定间隔限速替换为滑动窗口限速器，新增频率超限异常的退避重试处理

## Impact

- **数据库**：新增 2 张表（`scheduler_job_config`、`scheduler_execution_log`），需要 Alembic migration
- **代码模块**：
  - `src/shared/infrastructure/scheduler.py`：扩展 `SchedulerService`，支持从 DB 加载配置并自动注册
  - `src/modules/data_engineering/infrastructure/external_apis/tushare/client.py`：替换限速策略，新增异常退避
  - `src/modules/data_engineering/application/commands/sync_engine.py`：增强互斥检查逻辑，加入过期检测
  - `src/modules/data_engineering/presentation/rest/scheduler_routes.py`：HTTP API 操作同步写入 DB
- **配置**：新增 `SYNC_TASK_STALE_TIMEOUT_MINUTES`（默认 10）、`TUSHARE_RATE_LIMIT_WINDOW_SECONDS`（默认 60）、`TUSHARE_RATE_LIMIT_MAX_CALLS`（默认 195，预留安全余量）等配置项
- **API**：现有调度器 API 行为保持兼容，新增执行历史查询端点
- **依赖**：无新外部依赖
