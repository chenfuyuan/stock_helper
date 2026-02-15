## ADDED Requirements

### Requirement: 调度配置数据建模与持久化

系统 SHALL 在 `src/shared/infrastructure/scheduler/` 下定义调度配置的持久化模型。`SchedulerJobConfig` SHALL 包含以下字段：`id`（UUID，主键）、`job_id`（str，唯一标识，对应 JOB_REGISTRY 中的 key）、`job_name`（str，人类可读名称）、`cron_expression`（str，APScheduler cron 格式）、`timezone`（str，默认 `"Asia/Shanghai"`）、`enabled`（bool，是否启用）、`job_kwargs`（dict，任务参数）、`created_at`（datetime）、`updated_at`（datetime）、`last_run_at`（datetime，可为 null）。系统 SHALL 通过 Alembic migration 创建 `scheduler_job_config` 表。

#### Scenario: 调度配置表结构完整

- **WHEN** 审查 `scheduler_job_config` 表结构
- **THEN** 表 SHALL 包含上述所有字段，`job_id` 有唯一约束，`enabled` 默认为 `True`

#### Scenario: 通过 Repository 读写配置

- **WHEN** 系统需要查询或更新调度配置
- **THEN** SHALL 通过 `SchedulerJobConfigRepository` 进行，该 Repository 提供 `get_all_enabled()`、`get_by_job_id()`、`upsert()` 方法

---

### Requirement: 调度执行记录建模与持久化

系统 SHALL 定义 `SchedulerExecutionLog` 模型用于记录每次调度执行的详情。`SchedulerExecutionLog` SHALL 包含：`id`（UUID，主键）、`job_id`（str，关联的任务标识）、`started_at`（datetime，执行开始时间）、`finished_at`（datetime，执行结束时间，可为 null）、`status`（枚举：RUNNING / SUCCESS / FAILED）、`error_message`（str，失败时的错误信息，可为 null）、`duration_ms`（int，执行耗时毫秒数，可为 null）。系统 SHALL 通过 Alembic migration 创建 `scheduler_execution_log` 表。

#### Scenario: 执行记录表结构完整

- **WHEN** 审查 `scheduler_execution_log` 表结构
- **THEN** 表 SHALL 包含上述所有字段，`job_id` + `started_at` 有索引便于查询

#### Scenario: 通过 Repository 写入执行记录

- **WHEN** 系统需要记录一次调度执行
- **THEN** SHALL 通过 `SchedulerExecutionLogRepository` 进行，该 Repository 提供 `create()`、`update()`、`get_recent_by_job_id(job_id, limit)` 方法

---

### Requirement: 执行跟踪器（ExecutionTracker）

系统 SHALL 提供 `ExecutionTracker` 异步上下文管理器，用于包裹 job 函数的执行，自动记录执行日志。`ExecutionTracker` SHALL 在进入时创建一条 RUNNING 状态的 `SchedulerExecutionLog` 记录；正常退出时更新为 SUCCESS 并计算 `duration_ms`；异常退出时更新为 FAILED 并记录 `error_message`。`ExecutionTracker` 自身的持久化操作失败 SHALL NOT 中断被包裹的 job 执行，仅记录 ERROR 级别日志。

#### Scenario: 正常执行记录

- **WHEN** 一个 job 函数在 `ExecutionTracker` 上下文中正常完成
- **THEN** `SchedulerExecutionLog` 记录的 `status` SHALL 为 SUCCESS，`finished_at` 和 `duration_ms` 不为 null

#### Scenario: 异常执行记录

- **WHEN** 一个 job 函数在 `ExecutionTracker` 上下文中抛出异常
- **THEN** `SchedulerExecutionLog` 记录的 `status` SHALL 为 FAILED，`error_message` 包含异常信息，异常 SHALL 继续向上传播

#### Scenario: 日志持久化失败不中断 job

- **WHEN** `ExecutionTracker` 写入 `SchedulerExecutionLog` 时数据库连接失败
- **THEN** job 函数 SHALL 正常执行不受影响，系统记录 ERROR 级别日志

---

### Requirement: 应用启动自动注册调度任务

系统 SHALL 在应用启动时（`main.py` lifespan 中，`SchedulerService.start()` 之后）自动从数据库加载所有 `enabled=True` 的 `SchedulerJobConfig` 并注册到 APScheduler。`SchedulerService` SHALL 提供 `load_persisted_jobs(registry: Dict[str, Callable])` 方法，接受一个 job 注册表参数（`job_id → job_function` 映射），避免 `src/shared/` 反向依赖 `src/modules/`。对于 DB 中存在但注册表中找不到的 `job_id`，系统 SHALL 记录 WARNING 日志并跳过。加载过程的整体失败 SHALL NOT 阻止应用启动——退化为手动注册模式。

#### Scenario: 正常启动自动注册

- **WHEN** 应用启动，数据库中有 4 条 `enabled=True` 的调度配置，JOB_REGISTRY 中有对应的全部 4 个 job 函数
- **THEN** APScheduler SHALL 注册 4 个 cron 类型的 job，各 job 的 cron 表达式与 DB 配置一致

#### Scenario: 部分 job_id 未注册

- **WHEN** 数据库中有一条 `job_id=unknown_job` 的启用配置，但 JOB_REGISTRY 中无此 key
- **THEN** 系统 SHALL 记录 WARNING 日志并跳过该配置，其他有效配置正常注册

#### Scenario: 数据库不可用时退化

- **WHEN** 应用启动时数据库连接失败
- **THEN** `load_persisted_jobs()` SHALL 捕获异常、记录 ERROR 日志，应用正常启动（无自动注册的 job，可后续手动注册）

#### Scenario: disabled 配置不注册

- **WHEN** 数据库中有一条 `enabled=False` 的调度配置
- **THEN** 该 job SHALL NOT 被注册到 APScheduler

---

### Requirement: 预置默认调度计划

系统 SHALL 通过 Alembic migration 在 `scheduler_job_config` 表中 seed 以下默认调度配置（所有配置 `enabled=True`，`timezone=Asia/Shanghai`）：

| job_id | job_name | cron_expression | 说明 |
|--------|----------|-----------------|------|
| `sync_daily_by_date` | 日线增量同步 | `0 18 * * *` | 每天 18:00（北京时间） |
| `sync_incremental_finance` | 财务增量同步 | `0 0 * * *` | 每天 00:00（北京时间） |
| `sync_concept_data` | 概念数据同步 | `0 18 30 * * *` | 每天 18:30（北京时间） |
| `sync_stock_basic` | 股票基础信息同步 | `0 19 * * *` | 每天 19:00（北京时间） |

注意：此处仅 seed 增量/定期同步任务。历史全量同步（`sync_daily_history`、`sync_history_finance`）为一次性操作，不预置调度，保留手动触发方式。

#### Scenario: 首次部署后默认配置存在

- **WHEN** 执行 Alembic migration 后查询 `scheduler_job_config` 表
- **THEN** SHALL 存在上述 4 条默认记录，且 `enabled=True`

#### Scenario: 重复执行 migration 幂等

- **WHEN** Alembic migration 重复执行（如 `downgrade` 后 `upgrade`）
- **THEN** 默认配置不会重复插入（使用 `INSERT ... ON CONFLICT DO NOTHING` 或等效机制）

---

### Requirement: HTTP API 操作同步持久化

现有的调度器 HTTP API（`/scheduler/jobs/{job_id}/start`、`/schedule`、`/stop`）在操作 APScheduler 的同时，SHALL 将配置变更同步写入 `scheduler_job_config` 表（upsert 语义）。`/start`（interval 模式）和 `/schedule`（cron 模式）SHALL 更新或创建对应 `job_id` 的配置记录，`enabled=True`。`/stop` SHALL 将对应配置的 `enabled` 设为 `False`。

#### Scenario: schedule 操作持久化

- **WHEN** 调用 `POST /scheduler/jobs/sync_daily_by_date/schedule` 设置 `hour=20, minute=0`
- **THEN** APScheduler 注册对应 cron job，同时 `scheduler_job_config` 表中 `job_id=sync_daily_by_date` 的记录 SHALL 更新 `cron_expression` 为 `0 20 * * *`，`enabled=True`

#### Scenario: stop 操作持久化

- **WHEN** 调用 `POST /scheduler/jobs/sync_daily_by_date/stop`
- **THEN** APScheduler 移除对应 job，同时 `scheduler_job_config` 表中对应记录的 `enabled` SHALL 更新为 `False`

#### Scenario: 重启后保留手动修改

- **WHEN** 用户通过 API 将某 job 的 cron 从 `0 18 * * *` 修改为 `0 20 * * *`，然后重启应用
- **THEN** 应用启动后该 job 的调度时间 SHALL 为 20:00（从 DB 加载修改后的配置）

---

### Requirement: 调度执行历史查询 API

系统 SHALL 提供 `GET /scheduler/executions` 端点，返回调度执行历史列表。支持按 `job_id` 筛选，支持 `limit` 参数（默认 20，最大 100）。返回结果按 `started_at` 降序排列。每条记录包含 `job_id`、`started_at`、`finished_at`、`status`、`error_message`、`duration_ms`。

#### Scenario: 查询指定任务的执行历史

- **WHEN** 调用 `GET /scheduler/executions?job_id=sync_daily_by_date&limit=10`
- **THEN** 返回该任务最近 10 条执行记录，按 `started_at` 降序排列

#### Scenario: 查询所有任务的执行历史

- **WHEN** 调用 `GET /scheduler/executions`（无 job_id 参数）
- **THEN** 返回所有任务最近 20 条执行记录

#### Scenario: 无执行记录时返回空列表

- **WHEN** 查询一个从未执行过的 job_id
- **THEN** 返回空列表，HTTP 200
