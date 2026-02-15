## MODIFIED Requirements

### Requirement: 同步任务状态建模与持久化

系统 SHALL 在 data_engineering 的 Domain 层定义 `SyncTask` 实体和 `SyncFailureRecord` 实体，用于追踪同步任务的生命周期和失败记录。系统 SHALL 定义 `ISyncTaskRepository` Port（含创建、更新、按类型查询最近任务、查询未解决失败等方法），由 Infrastructure 层实现 PostgreSQL 持久化。`SyncTask` SHALL 包含：`id`、`job_type`（枚举：DAILY_HISTORY / FINANCE_HISTORY / DAILY_INCREMENTAL / FINANCE_INCREMENTAL / **AKSHARE_MARKET_DATA**）、`status`（枚举：PENDING / RUNNING / COMPLETED / FAILED / PAUSED）、`current_offset`、`batch_size`、`total_processed`、`started_at`、`updated_at`、`completed_at`、`config`（dict）。`SyncFailureRecord` SHALL 包含：`id`、`job_type`、`third_code`、`error_message`、`retry_count`、`max_retries`、`last_attempt_at`、`resolved_at`。系统 SHALL 通过 Alembic migration 创建对应的数据库表。

#### Scenario: 创建 AkShare 同步任务

- **WHEN** 系统启动 AkShare 市场数据同步
- **THEN** 系统 SHALL 通过 `ISyncTaskRepository` 创建一条 `SyncTask` 记录，`job_type` 为 `AKSHARE_MARKET_DATA`，状态为 RUNNING

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
