# Spec: de-data-sync

data_engineering 模块的统一数据同步能力：涵盖历史全量同步引擎（一次触发、自动分批、断点续跑）、增量同步（日线补偿与财务失败重试）、同步状态持久化、限速策略收敛、Presentation 层 DI 清理及配置外部化。

**测试约定**：每个 `#### Scenario:` 在变更**交付时**须对应至少一个自动化测试用例（单元或集成）；实现顺序可先实现再补测，以完整测试通过为需求完成标准。

---

## ADDED Requirements

### Requirement: 同步任务状态建模与持久化

系统 SHALL 在 data_engineering 的 Domain 层定义 `SyncTask` 实体和 `SyncFailureRecord` 实体，用于追踪同步任务的生命周期和失败记录。系统 SHALL 定义 `ISyncTaskRepository` Port（含创建、更新、按类型查询最近任务、查询未解决失败等方法），由 Infrastructure 层实现 PostgreSQL 持久化。`SyncTask` SHALL 包含：`id`、`job_type`（枚举：DAILY_HISTORY / FINANCE_HISTORY / DAILY_INCREMENTAL / FINANCE_INCREMENTAL）、`status`（枚举：PENDING / RUNNING / COMPLETED / FAILED / PAUSED）、`current_offset`、`batch_size`、`total_processed`、`started_at`、`updated_at`、`completed_at`、`config`（dict）。`SyncFailureRecord` SHALL 包含：`id`、`job_type`、`third_code`、`error_message`、`retry_count`、`max_retries`、`last_attempt_at`、`resolved_at`。系统 SHALL 通过 Alembic migration 创建对应的数据库表。

#### Scenario: 创建同步任务

- **WHEN** 系统启动一次历史同步或增量同步
- **THEN** 系统 SHALL 通过 `ISyncTaskRepository` 创建一条 `SyncTask` 记录，状态为 RUNNING，`current_offset` 初始为 0

#### Scenario: 更新同步进度

- **WHEN** 一批数据同步完成
- **THEN** 系统 SHALL 更新对应 `SyncTask` 的 `current_offset`、`total_processed` 和 `updated_at` 字段

#### Scenario: 记录同步失败

- **WHEN** 单只股票的同步过程中发生异常
- **THEN** 系统 SHALL 通过 `ISyncTaskRepository` 写入一条 `SyncFailureRecord`，包含 `third_code`、`error_message` 和 `retry_count=0`，并继续处理后续股票（不中断整批）

#### Scenario: 查询未解决的失败记录

- **WHEN** 增量同步需要执行失败重试
- **THEN** 系统 SHALL 通过 `ISyncTaskRepository` 查询 `resolved_at IS NULL AND retry_count < max_retries` 的 `SyncFailureRecord` 列表

---

### Requirement: 历史全量同步引擎——一次触发、跑完全量

系统 SHALL 在 Application 层提供 `SyncEngine` 应用服务，支持"一次触发、自动分批、跑完全量"的历史同步。`SyncEngine` SHALL 接受 `job_type` 和配置参数（`batch_size`、`start_date`、`end_date` 等），内部循环分批调用已有的同步 Use Case（`SyncDailyHistoryUseCase`、`SyncFinanceHistoryUseCase`），每批完成后更新 `SyncTask` 进度。当某批返回 0 条结果时 SHALL 标记任务为 COMPLETED。

#### Scenario: 一次触发历史日线全量同步

- **WHEN** 调用 `SyncEngine.run_history_sync(job_type=DAILY_HISTORY, config)` 且数据库中有 N 只股票
- **THEN** 系统 SHALL 自动分批循环（每批 `batch_size` 只股票），直到所有股票的历史日线数据同步完成，`SyncTask.status` 最终为 COMPLETED

#### Scenario: 一次触发历史财务全量同步

- **WHEN** 调用 `SyncEngine.run_history_sync(job_type=FINANCE_HISTORY, config)` 且配置了 `start_date` 和 `end_date`
- **THEN** 系统 SHALL 自动分批循环同步所有股票在指定日期范围内的财务指标数据，`SyncTask.status` 最终为 COMPLETED

#### Scenario: 同一类型同一时间只运行一个任务

- **WHEN** 调用 `SyncEngine.run_history_sync` 且已存在同类型 RUNNING 状态的 `SyncTask`
- **THEN** 系统 SHALL 拒绝启动新任务，返回已存在的 RUNNING 任务信息

---

### Requirement: 历史同步断点续跑

系统 SHALL 支持历史同步的断点续跑：当进程崩溃或手动中断后，再次触发同类型同步时，系统 SHALL 查找最近一条 RUNNING 或 PAUSED 状态的 `SyncTask`，从其 `current_offset` 处恢复，而非从头开始。

#### Scenario: 进程崩溃后恢复同步

- **WHEN** 历史同步在 offset=200 处中断（进程崩溃），然后重新触发同类型同步
- **THEN** 系统 SHALL 找到上次未完成的 `SyncTask`，从 `current_offset=200` 继续同步，不重复处理已完成的批次

#### Scenario: 手动暂停后恢复

- **WHEN** 用户通过 API 将 `SyncTask.status` 更新为 PAUSED，随后再次触发同步
- **THEN** 系统 SHALL 从 PAUSED 任务的 `current_offset` 处恢复

---

### Requirement: 增量日线同步——遗漏检测与自动补偿

增量日线同步 SHALL 在执行前查询数据库中最新的交易日期（`max(trade_date)`），与当前日期比较。若存在间隔（>1 个交易日），系统 SHALL 自动补同步缺失日期区间的日线数据，而非仅同步当天。正常无遗漏时，行为与当前一致（仅同步 today）。

#### Scenario: 无遗漏时同步当天数据

- **WHEN** 执行增量日线同步，且数据库中最新 `trade_date` 为昨天（前一个交易日）
- **THEN** 系统 SHALL 仅同步今天的日线数据

#### Scenario: 存在遗漏时自动补偿

- **WHEN** 执行增量日线同步，且数据库中最新 `trade_date` 为 3 天前
- **THEN** 系统 SHALL 自动补同步缺失日期区间（从 `max(trade_date) + 1` 到 today）的日线数据，每个缺失日期作为独立的同步批次

#### Scenario: 数据库为空时的行为

- **WHEN** 执行增量日线同步，且数据库中无任何日线记录
- **THEN** 系统 SHALL 记录警告日志并跳过补偿（此场景应通过历史全量同步处理），仅尝试同步今天

---

### Requirement: 增量财务同步——完善失败重试

增量财务同步 SHALL 在执行主流程（披露驱动 + 缺数补齐）前，先从 `SyncFailureRecord` 表查询该 `job_type` 下未解决且未超过最大重试次数的失败记录，优先重试。重试成功后 SHALL 更新 `resolved_at`；重试仍失败 SHALL 递增 `retry_count`。超过 `max_retries` 的记录 SHALL 保留在表中供人工排查，不再自动重试。

#### Scenario: 增量同步前先重试失败记录

- **WHEN** 执行增量财务同步，且 `SyncFailureRecord` 表中有 2 条 `retry_count < max_retries` 的未解决记录
- **THEN** 系统 SHALL 先重试这 2 条记录，然后再执行正常的披露驱动 + 缺数补齐流程

#### Scenario: 重试成功后标记已解决

- **WHEN** 失败重试成功拉取到该股票的财务数据
- **THEN** 系统 SHALL 更新该 `SyncFailureRecord` 的 `resolved_at` 为当前时间

#### Scenario: 重试仍失败则递增计数

- **WHEN** 失败重试再次失败
- **THEN** 系统 SHALL 递增 `retry_count` 并更新 `last_attempt_at`，不标记为 resolved

#### Scenario: 超过最大重试次数不再自动重试

- **WHEN** 某条 `SyncFailureRecord` 的 `retry_count >= max_retries`
- **THEN** 系统 SHALL NOT 自动重试该记录，保留在表中供人工排查

---

### Requirement: 限速策略收敛到 Infrastructure 层

所有 Tushare API 调用 SHALL 且仅 SHALL 通过 `TushareClient._rate_limited_call()` 进行限速。Application 层的同步 Use Case SHALL NOT 包含任何限速逻辑（如 `Semaphore`、`asyncio.sleep` 用于限速目的）。限速参数（最小调用间隔）SHALL 从配置中读取，而非硬编码。

#### Scenario: Use Case 无限速代码

- **WHEN** 审查 Application 层的所有同步 Use Case 代码
- **THEN** SHALL NOT 存在 `asyncio.Semaphore`、`asyncio.sleep`（用于限速目的）或其他限速控制逻辑

#### Scenario: 限速参数可配置

- **WHEN** 通过环境变量或配置文件设置 `TUSHARE_MIN_INTERVAL=0.5`
- **THEN** `TushareClient._rate_limited_call()` 使用 0.5s 作为最小调用间隔，而非硬编码值

---

### Requirement: Presentation 层依赖注入清理

`sync_scheduler.py`（Presentation 层）SHALL NOT 直接 import 或实例化 Infrastructure 层的类（如 `StockRepositoryImpl`、`TushareClient` 等）。Presentation 层 SHALL 通过工厂函数（如 `SyncUseCaseFactory`）获取已装配的 `SyncEngine` 或 Use Case 实例。工厂函数 SHALL 封装 session 创建和依赖组装逻辑。

#### Scenario: Scheduler Job 不直接依赖 Infrastructure

- **WHEN** 审查 `sync_scheduler.py` 的 import 语句
- **THEN** SHALL NOT 存在对 `infrastructure.persistence.repositories.*` 或 `infrastructure.external_apis.*` 的直接 import

#### Scenario: 通过工厂获取 SyncEngine

- **WHEN** Scheduler Job 需要执行同步任务
- **THEN** 通过 `SyncUseCaseFactory.create_sync_engine()` 获取已装配好的 `SyncEngine` 实例，工厂内部完成 session、repo、provider 的实例化和注入

---

### Requirement: 配置外部化

系统 SHALL 将以下硬编码值提取为可配置项（通过 `src/shared/config.py` 的 `Settings`，支持环境变量覆盖）：日线历史同步批大小（默认 50）、财务历史同步批大小（默认 100）、财务历史同步起始日期（默认 `20200101`）、增量同步缺数补齐上限（默认 300）、失败最大重试次数（默认 3）、Tushare 最小调用间隔（默认 0.35s）。Use Case 和 SyncEngine SHALL 从配置中读取这些值，而非硬编码。

#### Scenario: 通过环境变量覆盖批大小

- **WHEN** 设置环境变量 `SYNC_DAILY_HISTORY_BATCH_SIZE=100`
- **THEN** 历史日线同步使用 100 作为每批处理量，而非默认的 50

#### Scenario: 使用默认配置

- **WHEN** 未设置任何同步相关环境变量
- **THEN** 系统 SHALL 使用默认值运行（批大小 50/100、起始日期 20200101、限速 0.35s 等）

---

### Requirement: 同步任务事务边界

`SyncEngine` 在执行历史全量同步时，SHALL 每批使用独立的数据库 session（而非一个长事务跨越所有批次），避免长时间占用连接和锁。每批完成后 SHALL 提交事务并释放 session，然后为下一批创建新 session。

#### Scenario: 每批独立事务

- **WHEN** 历史同步引擎处理第 N 批和第 N+1 批数据
- **THEN** 第 N 批使用的数据库 session 在该批完成后即关闭，第 N+1 批使用新创建的 session

#### Scenario: 单批失败不影响已提交批次

- **WHEN** 第 N+1 批同步发生异常
- **THEN** 前 N 批已提交的数据 SHALL 保持不变（已持久化到数据库），系统记录进度为第 N 批的 offset

---

### Requirement: 删除旧的 JSON 文件状态管理

系统 SHALL 移除 `sync_scheduler.py` 中所有与 JSON 文件相关的状态管理代码（`load_offset`、`save_offset`、`load_finance_offset`、`save_finance_offset`、`load_finance_failures`、`save_finance_failures`、`append_finance_failures` 等函数及相关常量）。系统 SHALL 移除 `SyncIncrementalFinanceDataUseCase` 中的 `_save_failures` 方法及 `FAILURE_RECORD_FILE` 常量。所有进度和失败状态 SHALL 通过 `ISyncTaskRepository` 管理。

#### Scenario: 无 JSON 文件依赖

- **WHEN** 审查重构后的同步相关代码
- **THEN** SHALL NOT 存在对 `sync_daily_state.json`、`sync_finance_state.json`、`sync_finance_failures.json` 的任何读写操作

#### Scenario: Use Case 无内置失败文件管理

- **WHEN** 审查 `SyncIncrementalFinanceDataUseCase` 代码
- **THEN** SHALL NOT 存在 `_save_failures` 方法或对 `FAILURE_RECORD_FILE` 的引用
