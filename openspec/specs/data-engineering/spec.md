---
title: Data Engineering 模块规格
version: 1.0
last_updated: 2026-02-19
module: data-engineering
capabilities:
  - data-sync
  - clean-architecture
  - akshare-data-sync
  - financial-data-sanity
  - adapter-null-safety
  - indicator-data-sufficiency
  - concept-data-source
  - capital-flow-analysis
  - market-data-sync-api
source_specs:
  - de-data-sync
  - de-clean-arch-refactor
  - akshare-data-sync
  - financial-data-sanity
  - adapter-null-safety
  - indicator-data-sufficiency
  - concept-data-source
  - capital-flow-analysis
  - market-data-sync-api
---

# Data Engineering 模块规格

## Purpose

数据底座模块，负责行情、财报数据的 ETL、存储与查询。提供统一的数据同步引擎（历史全量、增量同步、断点续跑、失败重试）、AkShare 数据源接入（市场情绪、龙虎榜、板块资金流向、概念板块）、财务数据校验、适配器层空值安全等核心能力。

## Capabilities

| Capability | Description | Source |
|------------|-------------|--------|
| data-sync | 统一数据同步能力：历史全量同步引擎、增量同步、断点续跑、失败重试、限速策略 | de-data-sync |
| clean-architecture | 整洁架构合规重构：Presentation 层瘦身、Application 层服务化、Command 拆分与命名统一、DTO 合规整改 | de-clean-arch-refactor |
| akshare-data-sync | AkShare 数据源接入与同步：市场情绪数据（涨停池、炸板池、昨日涨停）、龙虎榜、板块资金流向 | akshare-data-sync |
| financial-data-sanity | 财务指标合理性校验：拦截上游数据异常，防止 LLM 在异常输入上产生不可靠结论 | financial-data-sanity |
| adapter-null-safety | 数据适配器层空值安全：对 daily 字段做 None 防护，收窄异常捕获范围，统一 third_code 取值来源 | adapter-null-safety |
| indicator-data-sufficiency | 技术指标数据量门槛校验：改进数据不足时的标记策略，确保 LLM 收到的输入可靠 | indicator-data-sufficiency |
| concept-data-source | 概念板块数据能力：外部数据获取、PostgreSQL 持久化和对外查询服务，为知识图谱提供数据底座 | concept-data-source |
| capital-flow-analysis | 市场主力资金行为分析：龙虎榜数据解析、板块/个股维度的资金净流入估算 | capital-flow-analysis |
| market-data-sync-api | 市场行情数据同步 HTTP API：提供 REST API 接口触发市场数据和概念数据的同步操作 | market-data-sync-api |

## General Conventions

### Requirement Language
- **SHALL** / **MUST**：强制性要求
- **SHOULD**：推荐性要求
- **MAY**：可选要求

### Testing Convention
每个 `#### Scenario:` 在变更交付时须对应至少一个自动化测试用例（单元或集成）；实现顺序可先实现再补测，以完整测试通过为需求完成标准。

---

## capability: data-sync

> Source: de-data-sync/spec.md (archived)

data_engineering 模块的统一数据同步能力：涵盖历史全量同步引擎（一次触发、自动分批、断点续跑）、增量同步（日线补偿与财务失败重试）、同步状态持久化、限速策略收敛、Presentation 层 DI 清理及配置外部化。

---

## Requirements

### Requirement: 同步任务状态建模与持久化

系统 SHALL 在 data_engineering 的 Domain 层定义 `SyncTask` 实体和 `SyncFailureRecord` 实体，用于追踪同步任务的生命周期和失败记录。系统 SHALL 定义 `ISyncTaskRepository` Port（含创建、更新、按类型查询最近任务、查询未解决失败等方法），由 Infrastructure 层实现 PostgreSQL 持久化。`SyncTask` SHALL 包含：`id`、`job_type`（枚举：DAILY_HISTORY / FINANCE_HISTORY / DAILY_INCREMENTAL / FINANCE_INCREMENTAL / AKSHARE_MARKET_DATA）、`status`（枚举：PENDING / RUNNING / COMPLETED / FAILED / PAUSED）、`current_offset`、`batch_size`、`total_processed`、`started_at`、`updated_at`、`completed_at`、`config`（dict）。`SyncFailureRecord` SHALL 包含：`id`、`job_type`、`third_code`、`error_message`、`retry_count`、`max_retries`、`last_attempt_at`、`resolved_at`。系统 SHALL 通过 Alembic migration 创建对应的数据库表。

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

### Requirement: 僵死任务超时检测与自动恢复

系统 SHALL 在 `SyncEngine.run_history_sync` 的互斥检查逻辑中增加基于 `updated_at` 的超时判断。当发现 RUNNING 状态的同类型 `SyncTask` 时，系统 SHALL 计算 `now - updated_at` 的时间差。若超过可配置的超时阈值（`SYNC_TASK_STALE_TIMEOUT_MINUTES`，默认 10 分钟），系统 SHALL 将该任务标记为 FAILED（失败原因记录为"超时自动标记：updated_at 超过阈值"），并允许启动新任务。若未超时，系统 SHALL 保持现有行为——拒绝启动新任务。

#### Scenario: RUNNING 任务超时自动标记为 FAILED

- **WHEN** 调用 `SyncEngine.run_history_sync`，已存在同类型 RUNNING 状态的 `SyncTask`，且其 `updated_at` 距今超过 10 分钟（默认阈值）
- **THEN** 系统 SHALL 将该 RUNNING 任务标记为 FAILED，记录超时原因，然后创建新的 `SyncTask` 并正常执行同步

#### Scenario: RUNNING 任务未超时仍拒绝新任务

- **WHEN** 调用 `SyncEngine.run_history_sync`，已存在同类型 RUNNING 状态的 `SyncTask`，且其 `updated_at` 距今在 10 分钟以内
- **THEN** 系统 SHALL 拒绝启动新任务，返回已存在的 RUNNING 任务信息（与现有行为一致）

#### Scenario: 超时阈值可配置

- **WHEN** 设置环境变量 `SYNC_TASK_STALE_TIMEOUT_MINUTES=5`
- **THEN** 系统 SHALL 使用 5 分钟作为超时阈值判断僵死任务

---

### Requirement: TuShare 频率超限异常退避重试

`TushareClient._rate_limited_call()` SHALL 在检测到 TuShare 返回频率超限异常时，自动执行指数退避重试。频率超限异常的判断 SHALL 基于异常消息中包含"频率"、"每分钟"等关键词。重试策略：第 1 次等待 3 秒，第 2 次 6 秒，第 3 次 12 秒（base=3s，factor=2）。超过 3 次重试后 SHALL 抛出原始异常由上层处理。每次重试 SHALL 记录 WARNING 级别日志，包含已重试次数和等待时间。

#### Scenario: 首次频率超限自动重试成功

- **WHEN** TuShare API 调用返回频率超限异常，第 1 次重试成功
- **THEN** 系统 SHALL 等待 3 秒后重试，重试成功后正常返回结果，上层调用方无感知

#### Scenario: 多次重试后成功

- **WHEN** TuShare API 连续 2 次返回频率超限异常，第 3 次成功
- **THEN** 系统 SHALL 依次等待 3 秒、6 秒后重试，第 3 次成功后正常返回结果

#### Scenario: 超过最大重试次数后抛出异常

- **WHEN** TuShare API 连续 4 次返回频率超限异常（首次 + 3 次重试均失败）
- **THEN** 系统 SHALL 抛出原始异常，由上层调用方处理

#### Scenario: 非频率超限异常不触发重试

- **WHEN** TuShare API 调用抛出网络超时或其他非频率相关异常
- **THEN** 系统 SHALL 直接抛出异常，不执行退避重试

---

### Requirement: 限速策略收敛到 Infrastructure 层

所有 Tushare API 调用 SHALL 且仅 SHALL 通过 `TushareClient._rate_limited_call()` 进行限速。Application 层的同步 Use Case SHALL NOT 包含任何限速逻辑（如 `Semaphore`、`asyncio.sleep` 用于限速目的）。限速 SHALL 采用**滑动窗口算法**（Sliding Window Log）：在 `TUSHARE_RATE_LIMIT_WINDOW_SECONDS`（默认 60 秒）的时间窗口内，允许最多 `TUSHARE_RATE_LIMIT_MAX_CALLS`（默认 195 次，预留安全余量）调用。当窗口内已达上限时，系统 SHALL 等待最早的时间戳滑出窗口后再执行调用。限速参数 SHALL 从配置中读取，而非硬编码。

#### Scenario: Use Case 无限速代码

- **WHEN** 审查 Application 层的所有同步 Use Case 代码
- **THEN** SHALL NOT 存在 `asyncio.Semaphore`、`asyncio.sleep`（用于限速目的）或其他限速控制逻辑

#### Scenario: 滑动窗口限速参数可配置

- **WHEN** 通过环境变量设置 `TUSHARE_RATE_LIMIT_MAX_CALLS=180` 和 `TUSHARE_RATE_LIMIT_WINDOW_SECONDS=60`
- **THEN** `TushareClient._rate_limited_call()` 在 60 秒窗口内最多允许 180 次调用

#### Scenario: 批量调用场景下吞吐量提升

- **WHEN** 系统在短时间内连续发起 100 次 TuShare API 调用，且当前窗口内已有 0 次记录
- **THEN** 前 100 次调用 SHALL 几乎无等待地连续执行（突发友好），总耗时远小于 100 × 0.35s = 35s

#### Scenario: 窗口内达到上限时等待

- **WHEN** 60 秒窗口内已完成 195 次调用，系统发起第 196 次调用
- **THEN** 系统 SHALL 等待最早的调用时间戳滑出 60 秒窗口后再执行第 196 次调用

---

### Requirement: 配置外部化

系统 SHALL 将以下硬编码值提取为可配置项（通过 `DataEngineeringConfig`，支持环境变量覆盖）：日线历史同步批大小（默认 50）、财务历史同步批大小（默认 100）、财务历史同步起始日期（默认 `20200101`）、增量同步缺数补齐上限（默认 300）、失败最大重试次数（默认 3）、**TuShare 滑动窗口最大调用次数**（默认 195）、**TuShare 滑动窗口时间秒数**（默认 60）、**同步任务僵死超时分钟数**（默认 10）。Use Case 和 SyncEngine SHALL 从配置中读取这些值，而非硬编码。

#### Scenario: 通过环境变量覆盖批大小

- **WHEN** 设置环境变量 `SYNC_DAILY_HISTORY_BATCH_SIZE=100`
- **THEN** 历史日线同步使用 100 作为每批处理量，而非默认的 50

#### Scenario: 通过环境变量覆盖滑动窗口参数

- **WHEN** 设置环境变量 `TUSHARE_RATE_LIMIT_MAX_CALLS=180`
- **THEN** TuShare 滑动窗口限速器使用 180 作为窗口内最大调用次数

#### Scenario: 通过环境变量覆盖僵死超时

- **WHEN** 设置环境变量 `SYNC_TASK_STALE_TIMEOUT_MINUTES=5`
- **THEN** 同步引擎使用 5 分钟作为僵死任务超时判断阈值

#### Scenario: 使用默认配置

- **WHEN** 未设置任何同步相关环境变量
- **THEN** 系统 SHALL 使用默认值运行（批大小 50/100、起始日期 20200101、滑动窗口 195次/60s、僵死超时 10 分钟等）

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

---

## capability: clean-architecture

> Source: de-clean-arch-refactor/spec.md (archived)

data_engineering 模块整洁架构合规重构：Presentation 层瘦身、Application 层服务化、Command 拆分与命名统一、DTO 合规整改、领域建模修正、返回值类型化、历史同步触发方式变更、日志与注释清理。

---

## Requirements

### Requirement: Presentation 层 Job 瘦身——仅做入口

Presentation 层的 Job 函数（`sync_scheduler.py`、`akshare_market_data_jobs.py`）SHALL 精简为纯入口函数（每个函数体 ≤10 行有效代码），仅负责调用 Application 层的 `DataSyncApplicationService` 对应方法。Job 函数 SHALL NOT 包含 session 管理、Container/Factory 构建、日期转换、ExecutionTracker 集成等编排逻辑。Job 函数 SHALL NOT 直接 import Infrastructure 层的任何类（包括本模块的 `de_config`、`AsyncSessionLocal`，以及其他模块的 `ExecutionTracker`、`SchedulerExecutionLogRepository`）。

#### Scenario: Job 函数仅调用 Application Service

- **WHEN** 审查 `presentation/jobs/` 下所有 Job 函数
- **THEN** 每个 Job 函数体 SHALL 仅包含：获取 `DataSyncApplicationService` 实例、调用对应方法、记录入口/出口日志，不包含 session 创建、Container 构建或 Infrastructure 类实例化

#### Scenario: Job 函数无 Infrastructure 层 import

- **WHEN** 审查 `presentation/jobs/` 下所有文件的 import 语句
- **THEN** SHALL NOT 存在对 `infrastructure.*`、`shared.infrastructure.*`、`foundation.infrastructure.*` 的直接 import

#### Scenario: Job 函数无跨模块 Infrastructure 依赖

- **WHEN** 审查 `presentation/jobs/` 下所有文件的 import 语句
- **THEN** SHALL NOT 存在对 `src.modules.foundation.infrastructure.*` 的 import（如 `ExecutionTracker`、`SchedulerExecutionLogRepository`）

---

### Requirement: stock_routes.py DI 清理

`presentation/rest/stock_routes.py` 中的依赖注入函数 SHALL NOT 直接构造 Infrastructure 层的实现类（如 `StockRepositoryImpl`、`StockDailyRepositoryImpl`、`TushareClient`）。SHALL 通过 `DataEngineeringContainer` 或工厂函数获取已装配的 Use Case 实例。

#### Scenario: REST Router 无 Infrastructure 直接 import

- **WHEN** 审查 `presentation/rest/stock_routes.py` 的 import 语句
- **THEN** SHALL NOT 存在对 `infrastructure.persistence.repositories.*` 或 `infrastructure.external_apis.*` 的直接 import

#### Scenario: DI 函数通过 Container 获取依赖

- **WHEN** REST Router 需要注入 Use Case 实例
- **THEN** SHALL 通过 `DataEngineeringContainer` 的工厂方法获取，而非手动构造 Repository 和 Provider

---

### Requirement: 文件与类命名统一

`application/commands/` 下所有文件 SHALL 使用 `_cmd.py` 后缀命名，文件名 SHALL 与主类名的 snake_case 形式一致。所有 Command 类 SHALL 使用 `XXXCmd` 命名模式（而非 `XXXUseCase`）。`application/queries/` 下的类保持 `XXXUseCase` 命名（Query 非 Command）。

#### Scenario: 文件重命名对照

- **WHEN** 重构完成后审查 `application/commands/` 目录
- **THEN** 以下文件 SHALL 已重命名：
  - `sync_daily_bar_cmd.py` → `sync_daily_by_date_cmd.py`（类名 `SyncDailyByDateCmd`）
  - `sync_daily_history.py` → `sync_daily_history_cmd.py`（类名 `SyncDailyHistoryCmd`）
  - `sync_finance_cmd.py` → `sync_finance_history_cmd.py`（类名 `SyncFinanceHistoryCmd`）
  - `sync_incremental_finance_data.py` → `sync_incremental_finance_cmd.py`（类名 `SyncIncrementalFinanceCmd`）
  - `sync_stock_list_cmd.py`（类名 `SyncStockListCmd`）

#### Scenario: 所有 import 路径同步更新

- **WHEN** 文件重命名后
- **THEN** 项目中所有引用旧路径的 import 语句 SHALL 已更新为新路径，`pytest` 通过无 ImportError

---

### Requirement: 拆分 SyncAkShareMarketDataCmd

`SyncAkShareMarketDataCmd` SHALL 拆分为 5 个独立的 Command，每个负责单一数据类型的同步：`SyncLimitUpPoolCmd`（涨停池）、`SyncBrokenBoardCmd`（炸板池）、`SyncPreviousLimitUpCmd`（昨日涨停）、`SyncDragonTigerCmd`（龙虎榜）、`SyncSectorCapitalFlowCmd`（板块资金流向）。原 `SyncAkShareMarketDataCmd` SHALL 保留为编排入口，依次调用上述 5 个 Command 并聚合结果，保持错误隔离（单类数据失败不中断其他类型）。

#### Scenario: 每个子 Command 独立可执行

- **WHEN** 单独调用 `SyncLimitUpPoolCmd.execute(trade_date)` 且 Provider 返回数据
- **THEN** SHALL 成功获取涨停池数据并通过 Repository 持久化，返回同步条数

#### Scenario: 编排 Command 聚合结果

- **WHEN** 调用 `SyncAkShareMarketDataCmd.execute(trade_date)` 且部分子 Command 失败
- **THEN** SHALL 返回 `AkShareSyncResult`，其中失败的子类型对应计数为 0，`errors` 列表包含失败信息，成功的子类型正常计数

#### Scenario: 子 Command 文件独立

- **WHEN** 审查 `application/commands/` 目录
- **THEN** SHALL 存在 5 个独立文件：`sync_limit_up_pool_cmd.py`、`sync_broken_board_cmd.py`、`sync_previous_limit_up_cmd.py`、`sync_dragon_tiger_cmd.py`、`sync_sector_capital_flow_cmd.py`

---

### Requirement: 历史全量同步改为 REST API 触发

`sync_daily_history` 和 `sync_history_finance` SHALL 从 `job_registry.py` 的 Job 注册表中移除。系统 SHALL 在 `presentation/rest/stock_routes.py` 新增 `POST /data/sync/daily-history` 和 `POST /data/sync/finance-history` 端点，通过 `DataSyncApplicationService` 触发历史全量同步，返回任务状态信息。

#### Scenario: Job Registry 不包含历史全量同步

- **WHEN** 审查 `job_registry.py` 的 `get_job_registry()` 返回值
- **THEN** SHALL NOT 包含 `sync_daily_history` 和 `sync_history_finance` 键

#### Scenario: REST API 触发历史日线同步

- **WHEN** 向 `POST /data/sync/daily-history` 发送请求
- **THEN** SHALL 触发日线历史全量同步并返回 SyncTask 状态信息（task_id、status）

#### Scenario: REST API 触发历史财务同步

- **WHEN** 向 `POST /data/sync/finance-history` 发送请求
- **THEN** SHALL 触发财务历史全量同步并返回 SyncTask 状态信息（task_id、status）

---

### Requirement: DTO 合规——消除 Entity 暴露与重复定义

1. `StockBasicInfoDTO` SHALL NOT 包含 Domain Entity 类型的字段。SHALL 将 `StockInfo` 和 `StockDaily` 的关键字段展开为基本类型（`third_code`、`symbol`、`name`、`industry`、`close`、`pct_chg` 等）。
2. `GetLimitUpPoolByDateUseCase`、`GetBrokenBoardByDateUseCase`、`GetDragonTigerByDateUseCase`、`GetPreviousLimitUpByDateUseCase` SHALL 返回对应的 DTO（如 `LimitUpPoolDTO`）而非 Domain Entity。
3. `DailyBarDTO` SHALL 合并为单一定义，提取到 `application/dtos/daily_bar_dto.py`，两个 Query 共用。
4. `ConceptSyncResult` SHALL 合并为单一定义，提取到 `application/dtos/sync_result_dtos.py`。

#### Scenario: StockBasicInfoDTO 不包含 Entity 引用

- **WHEN** 审查 `StockBasicInfoDTO` 的字段定义
- **THEN** 所有字段 SHALL 为基本类型（`str`、`int`、`float`、`date`、`Optional[...]`）或其他 DTO，SHALL NOT 引用 `StockInfo` 或 `StockDaily`

#### Scenario: AkShare Query 返回 DTO

- **WHEN** 调用 `GetLimitUpPoolByDateUseCase.execute(trade_date)`
- **THEN** SHALL 返回 `list[LimitUpPoolDTO]`（Pydantic DTO），非 `list[LimitUpPoolStock]`（Domain Entity）

#### Scenario: DailyBarDTO 单一定义

- **WHEN** 项目中搜索 `class DailyBarDTO`
- **THEN** SHALL 仅存在一处定义（在 `application/dtos/daily_bar_dto.py` 中）

#### Scenario: ConceptSyncResult 单一定义

- **WHEN** 项目中搜索 `class ConceptSyncResult`
- **THEN** SHALL 仅存在一处定义（在 `application/dtos/sync_result_dtos.py` 中）

---

### Requirement: 领域实体统一使用 Pydantic

`SyncTask` 和 `SyncFailureRecord` SHALL 从 `@dataclass` 迁移为继承项目的 `BaseEntity`（Pydantic `BaseModel`）。字段定义和行为方法（`start()`、`complete()`、`fail()`、`pause()`、`is_resumable()`、`can_retry()`、`increment_retry()` 等）保持不变。实体 SHALL NOT 设置 `frozen=True`（需支持 mutation）。

#### Scenario: SyncTask 为 Pydantic Model

- **WHEN** 审查 `domain/model/sync_task.py`
- **THEN** `SyncTask` SHALL 继承 `BaseEntity`（或 `pydantic.BaseModel`），不使用 `@dataclass`

#### Scenario: SyncFailureRecord 为 Pydantic Model

- **WHEN** 审查 `domain/model/sync_failure_record.py`
- **THEN** `SyncFailureRecord` SHALL 继承 `BaseEntity`（或 `pydantic.BaseModel`），不使用 `@dataclass`

#### Scenario: 行为方法正常工作

- **WHEN** 调用 `SyncTask.start()` 后再检查 `status`
- **THEN** `status` SHALL 为 `SyncTaskStatus.RUNNING`，`started_at` SHALL 非空

---

### Requirement: Command 返回值类型化

所有 `application/commands/` 下的 Command SHALL 使用类型化的 Pydantic DTO 作为返回值，SHALL NOT 返回 `Dict[str, Any]` 或 `Any`。返回值 DTO 统一定义在 `application/dtos/sync_result_dtos.py` 中。

#### Scenario: SyncDailyByDateCmd 返回类型化 DTO

- **WHEN** 调用 `SyncDailyByDateCmd.execute(trade_date)`
- **THEN** SHALL 返回 `DailyByDateSyncResult`（Pydantic DTO），含 `status`、`count`、`message` 字段

#### Scenario: SyncDailyHistoryCmd 返回类型化 DTO

- **WHEN** 调用 `SyncDailyHistoryCmd.execute(limit, offset)`
- **THEN** SHALL 返回 `DailyHistorySyncResult`（Pydantic DTO），含 `synced_stocks`、`total_rows`、`message` 字段

#### Scenario: 无 Dict[str, Any] 返回

- **WHEN** 审查 `application/commands/` 下所有 Command 的 `execute` 方法签名
- **THEN** SHALL NOT 存在 `-> Dict[str, Any]` 或 `-> Any` 返回类型注解

---

### Requirement: 日志语言统一为中文

所有 data_engineering 模块的日志内容 SHALL 使用中文（符合 tech-standards 日志规范）。以下文件中的英文日志 SHALL 替换为中文：`sync_daily_bar_cmd.py`（重命名后 `sync_daily_by_date_cmd.py`）、`sync_finance_cmd.py`（重命名后 `sync_finance_history_cmd.py`）、`presentation/rest/stock_routes.py`。

#### Scenario: 无英文日志内容

- **WHEN** 审查 data_engineering 模块中所有 `logger.info/warning/error` 调用
- **THEN** 日志消息内容 SHALL 使用中文

---

### Requirement: 遗留代码清理

1. `sync_stock_list_cmd.py` 中 Lines 13-19 的 debug 思路注释 SHALL 删除。
2. `akshare_market_data_jobs.py` 中 Line 36 的重复 `from datetime import datetime` SHALL 删除。
3. 所有 `application/commands/` 下的 Command 类 SHALL 统一 `BaseUseCase` 继承策略：Command 继承 `BaseUseCase`，或全部不继承（二选一，保持一致）。

#### Scenario: 无遗留 debug 注释

- **WHEN** 审查 `sync_stock_list_cmd.py`（重命名前）
- **THEN** SHALL NOT 存在 "Fix DTO import"、"I'll check if I moved" 等 debug 思路注释

#### Scenario: 无重复 import

- **WHEN** 审查 `akshare_market_data_jobs.py`
- **THEN** SHALL NOT 存在对同一模块的重复 import 语句

---

### Requirement: DataSyncApplicationService

系统 SHALL 在 `application/services/` 下新增 `DataSyncApplicationService`，作为所有数据同步任务的统一编排入口。该服务 SHALL 封装 session 管理、Container/Factory 获取、ExecutionTracker 集成等逻辑，对外暴露简洁的异步方法供 Presentation 层调用。

#### Scenario: Service 提供所有同步入口

- **WHEN** 审查 `DataSyncApplicationService` 的公开方法
- **THEN** SHALL 包含以下方法：`run_daily_incremental_sync`、`run_incremental_finance_sync`、`run_concept_sync`、`run_akshare_market_data_sync`、`run_stock_basic_sync`、`run_daily_history_sync`、`run_finance_history_sync`

#### Scenario: Service 内部管理 ExecutionTracker

- **WHEN** 通过 `DataSyncApplicationService.run_daily_incremental_sync()` 触发同步
- **THEN** SHALL 自动创建 ExecutionTracker 记录执行日志，Presentation 层无需感知

---

### Requirement: AkShare Query DTO 定义

系统 SHALL 在 `application/dtos/` 下为 AkShare 相关 Query 新增对应 DTO：`LimitUpPoolDTO`、`BrokenBoardDTO`、`DragonTigerDTO`、`PreviousLimitUpDTO`、`SectorCapitalFlowDTO`。DTO 字段 SHALL 为基本类型，与对应 Domain Entity 的对外可见字段一致。

#### Scenario: DTO 字段覆盖 Entity 对外字段

- **WHEN** 审查 `LimitUpPoolDTO` 的字段
- **THEN** SHALL 包含 `trade_date`、`third_code`、`stock_name`、`pct_chg`、`close`、`amount`、`turnover_rate`、`consecutive_boards`、`first_limit_up_time`、`last_limit_up_time`、`industry` 字段

---

## capability: akshare-data-sync

> Source: akshare-data-sync/spec.md (archived)

AkShare 数据源的接入与同步能力，涵盖市场情绪数据（涨停池、炸板池、昨日涨停表现）、龙虎榜详情、板块资金流向等增强数据的采集、持久化和查询。支持按日期快照同步，具备限速保护和异常隔离机制。

---

## Requirements

### Requirement: AkShare 基类提取

系统 MUST 在 `data_engineering/infrastructure/external_apis/akshare/base_client.py` 中定义 `AkShareBaseClient` 基类，封装 AkShare API 调用的通用逻辑。

基类 MUST 提供以下能力：
- `_run_in_executor(func, *args, **kwargs)`: 在线程池中执行同步 AkShare API 调用，避免阻塞事件循环
- `_rate_limited_call(func, *args, **kwargs)`: 带进程级限速的 API 调用，使用全局共享锁控制调用频率
- `request_interval`（可配置，默认 0.3s）

现有 `AkShareConceptClient` MUST 重构为继承 `AkShareBaseClient`，移除重复的限速和异步执行代码。

#### Scenario: 基类限速逻辑复用

- **WHEN** `AkShareMarketDataClient` 和 `AkShareConceptClient` 同时发起 API 调用
- **THEN** 两者 MUST 共享同一个进程级限速锁，调用间隔不小于 `request_interval`

#### Scenario: 现有功能不受影响

- **WHEN** `AkShareConceptClient` 重构为继承 `AkShareBaseClient` 后
- **THEN** `fetch_concept_list()` 和 `fetch_concept_constituents()` 的行为 MUST 与重构前完全一致

---

### Requirement: IMarketSentimentProvider 接口定义

系统 MUST 在 `data_engineering/domain/ports/providers/market_sentiment_provider.py` 中定义 `IMarketSentimentProvider` ABC 接口，用于获取市场情绪相关数据。

该接口 MUST 包含以下方法：

- `fetch_limit_up_pool(trade_date: date) -> list[LimitUpPoolDTO]`：获取指定日期的涨停池数据（含连板天数）
- `fetch_broken_board_pool(trade_date: date) -> list[BrokenBoardDTO]`：获取指定日期的炸板池数据
- `fetch_previous_limit_up(trade_date: date) -> list[PreviousLimitUpDTO]`：获取昨日涨停股今日表现数据

所有方法 MUST 为异步方法（async）。

`LimitUpPoolDTO` 字段 MUST 包含：
- `third_code`（str）：股票代码（系统标准格式，如 `000001.SZ`）
- `stock_name`（str）：股票名称
- `pct_chg`（float）：涨跌幅（百分比）
- `close`（float）：最新价
- `amount`（float）：成交额
- `turnover_rate`（float）：换手率
- `consecutive_boards`（int）：连板天数（首板为 1）
- `first_limit_up_time`（str | None）：首次封板时间
- `last_limit_up_time`（str | None）：最后封板时间
- `industry`（str）：所属行业

`BrokenBoardDTO` 字段 MUST 包含：
- `third_code`（str）：股票代码
- `stock_name`（str）：股票名称
- `pct_chg`（float）：涨跌幅
- `close`（float）：最新价
- `amount`（float）：成交额
- `turnover_rate`（float）：换手率
- `open_count`（int）：开板次数
- `first_limit_up_time`（str | None）：首次封板时间
- `last_open_time`（str | None）：最后开板时间
- `industry`（str）：所属行业

`PreviousLimitUpDTO` 字段 MUST 包含：
- `third_code`（str）：股票代码
- `stock_name`（str）：股票名称
- `pct_chg`（float）：今日涨跌幅
- `close`（float）：最新价
- `amount`（float）：成交额
- `turnover_rate`（float）：换手率
- `yesterday_consecutive_boards`（int）：昨日连板天数
- `industry`（str）：所属行业

所有 DTO MUST 定义在 `data_engineering/domain/dtos/market_sentiment_dtos.py` 中。

#### Scenario: Port 在 Domain 层定义

- **WHEN** 检查 `IMarketSentimentProvider` 的定义位置
- **THEN** MUST 位于 `data_engineering/domain/ports/providers/market_sentiment_provider.py`
- **THEN** 返回类型 MUST 使用 `data_engineering` 领域层定义的 DTO

---

### Requirement: IDragonTigerProvider 接口定义

系统 MUST 在 `data_engineering/domain/ports/providers/dragon_tiger_provider.py` 中定义 `IDragonTigerProvider` ABC 接口。

该接口 MUST 包含以下方法：

- `fetch_dragon_tiger_detail(trade_date: date) -> list[DragonTigerDetailDTO]`：获取指定日期的龙虎榜详情数据

方法 MUST 为异步方法（async）。

`DragonTigerDetailDTO` 字段 MUST 包含：
- `third_code`（str）：股票代码
- `stock_name`（str）：股票名称
- `pct_chg`（float）：涨跌幅
- `close`（float）：收盘价
- `reason`（str）：上榜原因
- `net_amount`（float）：龙虎榜净买入额
- `buy_amount`（float）：买入总额
- `sell_amount`（float）：卖出总额
- `buy_seats`（list[dict]）：买入席位详情列表，每项包含 `seat_name`（str）和 `buy_amount`（float）
- `sell_seats`（list[dict]）：卖出席位详情列表，每项包含 `seat_name`（str）和 `sell_amount`（float）

DTO MUST 定义在 `data_engineering/domain/dtos/dragon_tiger_dtos.py` 中。

#### Scenario: Port 在 Domain 层定义

- **WHEN** 检查 `IDragonTigerProvider` 的定义位置
- **THEN** MUST 位于 `data_engineering/domain/ports/providers/dragon_tiger_provider.py`

---

### Requirement: ISectorCapitalFlowProvider 接口定义

系统 MUST 在 `data_engineering/domain/ports/providers/sector_capital_flow_provider.py` 中定义 `ISectorCapitalFlowProvider` ABC 接口。

该接口 MUST 包含以下方法：

- `fetch_sector_capital_flow(sector_type: str = "概念资金流") -> list[SectorCapitalFlowDTO]`：获取当日板块资金流向排名

方法 MUST 为异步方法（async）。

`SectorCapitalFlowDTO` 字段 MUST 包含：
- `sector_name`（str）：板块名称
- `sector_type`（str）：板块类型（如"概念资金流"）
- `net_amount`（float）：净流入额（万元）
- `inflow_amount`（float）：流入额（万元）
- `outflow_amount`（float）：流出额（万元）
- `pct_chg`（float）：板块涨跌幅

DTO MUST 定义在 `data_engineering/domain/dtos/capital_flow_dtos.py` 中。

#### Scenario: Port 在 Domain 层定义

- **WHEN** 检查 `ISectorCapitalFlowProvider` 的定义位置
- **THEN** MUST 位于 `data_engineering/domain/ports/providers/sector_capital_flow_provider.py`

---

### Requirement: AkShareMarketDataClient 适配器实现

系统 MUST 在 `data_engineering/infrastructure/external_apis/akshare/market_data_client.py` 中实现 `AkShareMarketDataClient`，继承 `AkShareBaseClient`，并实现 `IMarketSentimentProvider`、`IDragonTigerProvider`、`ISectorCapitalFlowProvider` 三个接口。

该客户端 MUST 调用以下 AkShare API：
- 涨停池：`ak.stock_zt_pool_em(date=<yyyymmdd>)`
- 炸板池：`ak.stock_zt_pool_zbgc_em(date=<yyyymmdd>)`
- 昨日涨停表现：`ak.stock_zt_pool_previous_em(date=<yyyymmdd>)`
- 龙虎榜详情：`ak.stock_lhb_detail_em(start_date=<yyyymmdd>, end_date=<yyyymmdd>)`
- 板块资金流向：`ak.stock_sector_fund_flow_rank(indicator="今日", sector_type=<type>)`

股票代码 MUST 使用 `stock_code_converter` 转换为系统标准格式。

每个 `fetch_*` 方法 MUST：
1. 通过 `_rate_limited_call` 执行 API 调用
2. 处理空返回（返回空列表，记录 WARNING 日志）
3. 捕获 `ImportError` 抛出 `AppException(code="AKSHARE_IMPORT_ERROR")`
4. 捕获其他异常抛出 `AppException(code="AKSHARE_API_ERROR")`

#### Scenario: 正常获取涨停池数据

- **WHEN** 调用 `fetch_limit_up_pool(date(2024, 2, 15))`，AkShare API 返回有效数据
- **THEN** 系统 MUST 返回 `list[LimitUpPoolDTO]`，股票代码为系统标准格式，`consecutive_boards` 正确解析

#### Scenario: API 返回空数据

- **WHEN** 调用 `fetch_limit_up_pool(date(2024, 2, 15))`，AkShare 返回空 DataFrame
- **THEN** 系统 MUST 返回空列表并记录 WARNING 日志

#### Scenario: AkShare 未安装

- **WHEN** 调用任意 `fetch_*` 方法但 `akshare` 库未安装
- **THEN** 系统 MUST 抛出 `AppException(code="AKSHARE_IMPORT_ERROR")`

#### Scenario: API 调用失败

- **WHEN** 调用任意 `fetch_*` 方法时 AkShare API 抛出异常
- **THEN** 系统 MUST 抛出 `AppException(code="AKSHARE_API_ERROR")`，details 包含原始错误信息

---

### Requirement: 涨停池数据领域实体与持久化

系统 MUST 在 `data_engineering/domain/model/limit_up_pool.py` 中定义 `LimitUpPoolStock` 领域实体（继承 Pydantic `BaseModel`）。

字段 MUST 包含：
- `trade_date`（date）：交易日期
- `third_code`（str）：股票代码
- `stock_name`（str）：股票名称
- `pct_chg`（float）：涨跌幅
- `close`（float）：最新价
- `amount`（float）：成交额
- `turnover_rate`（float）：换手率
- `consecutive_boards`（int）：连板天数
- `first_limit_up_time`（str | None）：首次封板时间
- `last_limit_up_time`（str | None）：最后封板时间
- `industry`（str）：所属行业

系统 MUST 在 `data_engineering/domain/ports/repositories/limit_up_pool_repo.py` 中定义 `ILimitUpPoolRepository` ABC 接口，包含：
- `save_all(stocks: list[LimitUpPoolStock]) -> int`：批量 UPSERT，以 `(trade_date, third_code)` 为唯一键
- `get_by_date(trade_date: date) -> list[LimitUpPoolStock]`：查询指定日期涨停池

系统 MUST 在 `data_engineering/infrastructure/persistence/` 下实现 PostgreSQL 持久化：
- ORM Model：`LimitUpPoolModel` 映射 `de_limit_up_pool` 表
- Repository：`PgLimitUpPoolRepository` 实现 `ILimitUpPoolRepository`
- Alembic Migration：创建 `de_limit_up_pool` 表，`(trade_date, third_code)` 唯一约束

#### Scenario: 批量 UPSERT 涨停池数据

- **WHEN** 调用 `save_all` 传入 10 条涨停池数据，其中 3 条与已有记录键冲突
- **THEN** 系统 MUST 插入 7 条新记录并更新 3 条已有记录，返回影响行数 10

#### Scenario: 按日期查询涨停池

- **WHEN** 调用 `get_by_date(date(2024, 2, 15))`
- **THEN** 系统 MUST 返回该日期的所有涨停池记录

---

### Requirement: 炸板池数据领域实体与持久化

系统 MUST 在 `data_engineering/domain/model/broken_board.py` 中定义 `BrokenBoardStock` 领域实体（继承 Pydantic `BaseModel`）。

字段 MUST 包含：
- `trade_date`（date）：交易日期
- `third_code`（str）：股票代码
- `stock_name`（str）：股票名称
- `pct_chg`（float）：涨跌幅
- `close`（float）：最新价
- `amount`（float）：成交额
- `turnover_rate`（float）：换手率
- `open_count`（int）：开板次数
- `first_limit_up_time`（str | None）：首次封板时间
- `last_open_time`（str | None）：最后开板时间
- `industry`（str）：所属行业

系统 MUST 在 `data_engineering/domain/ports/repositories/broken_board_repo.py` 中定义 `IBrokenBoardRepository` ABC 接口，包含：
- `save_all(stocks: list[BrokenBoardStock]) -> int`：批量 UPSERT，以 `(trade_date, third_code)` 为唯一键
- `get_by_date(trade_date: date) -> list[BrokenBoardStock]`：查询指定日期炸板池

系统 MUST 实现对应的 ORM Model（`BrokenBoardModel` → `de_broken_board_pool` 表）和 PostgreSQL Repository。

#### Scenario: 批量 UPSERT 炸板池数据

- **WHEN** 调用 `save_all` 传入炸板池数据
- **THEN** 系统 MUST 以 `(trade_date, third_code)` 为唯一键执行 UPSERT

#### Scenario: 按日期查询炸板池

- **WHEN** 调用 `get_by_date(date(2024, 2, 15))`
- **THEN** 系统 MUST 返回该日期的所有炸板池记录

---

### Requirement: 昨日涨停表现数据领域实体与持久化

系统 MUST 在 `data_engineering/domain/model/previous_limit_up.py` 中定义 `PreviousLimitUpStock` 领域实体（继承 Pydantic `BaseModel`）。

字段 MUST 包含：
- `trade_date`（date）：交易日期（今日日期，即表现观察日）
- `third_code`（str）：股票代码
- `stock_name`（str）：股票名称
- `pct_chg`（float）：今日涨跌幅
- `close`（float）：最新价
- `amount`（float）：成交额
- `turnover_rate`（float）：换手率
- `yesterday_consecutive_boards`（int）：昨日连板天数
- `industry`（str）：所属行业

系统 MUST 定义 `IPreviousLimitUpRepository` 接口（含 `save_all`、`get_by_date`）并实现 PostgreSQL 持久化（`de_previous_limit_up` 表，`(trade_date, third_code)` 唯一约束）。

#### Scenario: 批量 UPSERT 昨日涨停表现

- **WHEN** 调用 `save_all` 传入昨日涨停表现数据
- **THEN** 系统 MUST 以 `(trade_date, third_code)` 为唯一键执行 UPSERT

#### Scenario: 按日期查询昨日涨停表现

- **WHEN** 调用 `get_by_date(date(2024, 2, 15))`
- **THEN** 系统 MUST 返回该日期的所有昨日涨停表现记录

---

### Requirement: 龙虎榜数据领域实体与持久化

系统 MUST 在 `data_engineering/domain/model/dragon_tiger.py` 中定义 `DragonTigerDetail` 领域实体（继承 Pydantic `BaseModel`）。

字段 MUST 包含：
- `trade_date`（date）：交易日期
- `third_code`（str）：股票代码
- `stock_name`（str）：股票名称
- `pct_chg`（float）：涨跌幅
- `close`（float）：收盘价
- `reason`（str）：上榜原因
- `net_amount`（float）：龙虎榜净买入额
- `buy_amount`（float）：买入总额
- `sell_amount`（float）：卖出总额
- `buy_seats`（list[dict]）：买入席位详情（JSONB 存储）
- `sell_seats`（list[dict]）：卖出席位详情（JSONB 存储）

系统 MUST 定义 `IDragonTigerRepository` 接口，包含：
- `save_all(details: list[DragonTigerDetail]) -> int`：批量 UPSERT，以 `(trade_date, third_code, reason)` 为唯一键
- `get_by_date(trade_date: date) -> list[DragonTigerDetail]`：查询指定日期龙虎榜

系统 MUST 实现 ORM Model（`DragonTigerModel` → `de_dragon_tiger` 表）和 PostgreSQL Repository。`buy_seats` 和 `sell_seats` MUST 使用 JSONB 类型存储。

#### Scenario: 批量 UPSERT 龙虎榜数据

- **WHEN** 调用 `save_all` 传入龙虎榜数据，其中同一股票可因不同上榜原因有多条记录
- **THEN** 系统 MUST 以 `(trade_date, third_code, reason)` 为唯一键执行 UPSERT

#### Scenario: 按日期查询龙虎榜

- **WHEN** 调用 `get_by_date(date(2024, 2, 15))`
- **THEN** 系统 MUST 返回该日期的所有龙虎榜记录，含席位详情

---

### Requirement: 板块资金流向数据领域实体与持久化

系统 MUST 在 `data_engineering/domain/model/sector_capital_flow.py` 中定义 `SectorCapitalFlow` 领域实体（继承 Pydantic `BaseModel`）。

字段 MUST 包含：
- `trade_date`（date）：交易日期
- `sector_name`（str）：板块名称
- `sector_type`（str）：板块类型（如"概念资金流"）
- `net_amount`（float）：净流入额（万元）
- `inflow_amount`（float）：流入额（万元）
- `outflow_amount`（float）：流出额（万元）
- `pct_chg`（float）：板块涨跌幅

系统 MUST 定义 `ISectorCapitalFlowRepository` 接口，包含：
- `save_all(flows: list[SectorCapitalFlow]) -> int`：批量 UPSERT，以 `(trade_date, sector_name, sector_type)` 为唯一键
- `get_by_date(trade_date: date, sector_type: str | None = None) -> list[SectorCapitalFlow]`：查询指定日期板块资金流向

系统 MUST 实现 ORM Model（`SectorCapitalFlowModel` → `de_sector_capital_flow` 表）和 PostgreSQL Repository。

#### Scenario: 批量 UPSERT 板块资金流向

- **WHEN** 调用 `save_all` 传入板块资金流向数据
- **THEN** 系统 MUST 以 `(trade_date, sector_name, sector_type)` 为唯一键执行 UPSERT

#### Scenario: 按日期查询板块资金流向

- **WHEN** 调用 `get_by_date(date(2024, 2, 15))`
- **THEN** 系统 MUST 返回该日期的所有板块资金流向记录

#### Scenario: 按日期和板块类型过滤

- **WHEN** 调用 `get_by_date(date(2024, 2, 15), sector_type="概念资金流")`
- **THEN** 系统 MUST 仅返回"概念资金流"类型的记录

---

### Requirement: SyncAkShareMarketDataCmd 同步命令

系统 MUST 在 `data_engineering/application/commands/sync_akshare_market_data_cmd.py` 中实现 `SyncAkShareMarketDataCmd` 应用命令。

该命令 MUST 编排以下同步流程：

1. 通过 `IMarketSentimentProvider` 获取涨停池、炸板池、昨日涨停表现
2. 通过 `IDragonTigerProvider` 获取龙虎榜详情
3. 通过 `ISectorCapitalFlowProvider` 获取板块资金流向
4. 将 DTO 转换为领域实体
5. 通过对应 Repository 批量 UPSERT 持久化

接口签名：
```
execute(trade_date: date) -> AkShareSyncResult
```

`AkShareSyncResult` 为 Application 层 DTO，字段 MUST 包含：
- `trade_date`（date）
- `limit_up_pool_count`（int）：涨停池记录数
- `broken_board_count`（int）：炸板池记录数
- `previous_limit_up_count`（int）：昨日涨停表现记录数
- `dragon_tiger_count`（int）：龙虎榜记录数
- `sector_capital_flow_count`（int）：板块资金流向记录数
- `errors`（list[str]）：各类数据同步失败的错误信息列表

单类数据采集失败 MUST NOT 中断其他类型的同步，错误信息记录到 `errors` 列表并记录 ERROR 日志。

#### Scenario: 正常全量同步

- **WHEN** 调用 `execute(date(2024, 2, 15))`，所有 AkShare API 正常返回
- **THEN** 系统 MUST 依次采集 5 类数据并持久化，返回各类记录数，`errors` 为空列表

#### Scenario: 部分数据采集失败

- **WHEN** 调用 `execute(date(2024, 2, 15))`，龙虎榜 API 调用失败但其余正常
- **THEN** 系统 MUST 持久化其余 4 类数据，`dragon_tiger_count` 为 0，`errors` 包含龙虎榜的错误信息

#### Scenario: 幂等同步

- **WHEN** 对同一 `trade_date` 连续调用两次 `execute`
- **THEN** 第二次调用 MUST 通过 UPSERT 更新已有记录，不产生重复数据

---

### Requirement: AkShare 数据查询用例

系统 MUST 在 `data_engineering/application/queries/` 下提供以下查询用例，供 `market_insight` 模块通过 Ports 消费：

1. `GetLimitUpPoolByDateUseCase`：
   - 签名：`execute(trade_date: date) -> list[LimitUpPoolStock]`
   - 位置：`get_limit_up_pool_by_date.py`

2. `GetBrokenBoardByDateUseCase`：
   - 签名：`execute(trade_date: date) -> list[BrokenBoardStock]`
   - 位置：`get_broken_board_by_date.py`

3. `GetPreviousLimitUpByDateUseCase`：
   - 签名：`execute(trade_date: date) -> list[PreviousLimitUpStock]`
   - 位置：`get_previous_limit_up_by_date.py`

4. `GetDragonTigerByDateUseCase`：
   - 签名：`execute(trade_date: date) -> list[DragonTigerDetail]`
   - 位置：`get_dragon_tiger_by_date.py`

5. `GetSectorCapitalFlowByDateUseCase`：
   - 签名：`execute(trade_date: date, sector_type: str | None = None) -> list[SectorCapitalFlow]`
   - 位置：`get_sector_capital_flow_by_date.py`

每个查询用例 MUST 通过对应的 Repository Port 查询数据。

#### Scenario: 查询涨停池

- **WHEN** 调用 `GetLimitUpPoolByDateUseCase.execute(date(2024, 2, 15))`
- **THEN** 系统 MUST 通过 `ILimitUpPoolRepository.get_by_date` 返回该日期涨停池数据

#### Scenario: 查询龙虎榜

- **WHEN** 调用 `GetDragonTigerByDateUseCase.execute(date(2024, 2, 15))`
- **THEN** 系统 MUST 通过 `IDragonTigerRepository.get_by_date` 返回该日期龙虎榜数据

---

### Requirement: DI 容器扩展

系统 MUST 更新 `data_engineering/container.py` 的 `DataEngineeringContainer`，注册以下新增依赖：

- `AkShareMarketDataClient` 实例（实现 `IMarketSentimentProvider`、`IDragonTigerProvider`、`ISectorCapitalFlowProvider`）
- `PgLimitUpPoolRepository`、`PgBrokenBoardRepository`、`PgPreviousLimitUpRepository`、`PgDragonTigerRepository`、`PgSectorCapitalFlowRepository`
- `SyncAkShareMarketDataCmd`
- 各查询用例（`GetLimitUpPoolByDateUseCase` 等）

容器 MUST 提供工厂方法用于获取：
- `get_sync_akshare_market_data_cmd() -> SyncAkShareMarketDataCmd`
- `get_limit_up_pool_by_date_use_case() -> GetLimitUpPoolByDateUseCase`
- `get_broken_board_by_date_use_case() -> GetBrokenBoardByDateUseCase`
- `get_previous_limit_up_by_date_use_case() -> GetPreviousLimitUpByDateUseCase`
- `get_dragon_tiger_by_date_use_case() -> GetDragonTigerByDateUseCase`
- `get_sector_capital_flow_by_date_use_case() -> GetSectorCapitalFlowByDateUseCase`

#### Scenario: 容器注册完整性

- **WHEN** 通过 `DataEngineeringContainer` 获取 `SyncAkShareMarketDataCmd`
- **THEN** 系统 MUST 返回正确装配的实例，内部注入了所有 Provider 和 Repository 依赖

---

## capability: financial-data-sanity

> Source: financial-data-sanity/spec.md (archived)

在估值快照构建阶段增加财务指标合理性校验，拦截上游数据异常（如毛利率 4500 万%），防止 LLM 在异常输入上产生不可靠的分析结论。涉及 ValuationSnapshotBuilderImpl 及毛利率趋势计算。

---

## Requirements

### Requirement: 关键财务指标合理性边界校验

`ValuationSnapshotBuilderImpl.build()` 在将上游财务数据填入 `ValuationSnapshotDTO` 前，SHALL 对以下关键财务指标进行合理性边界校验。超出合理范围的值 SHALL 被替换为 `"N/A"`（与 `PlaceholderValue` 类型兼容），并记录 WARNING 级别日志（包含字段名、原始值、标的信息）。

校验范围（业务合理性阈值）：
- **毛利率 (gross_margin)**：有效范围 [-100, 100]。毛利率定义为 (营收-成本)/营收，理论上不可能超出 ±100%。
- **ROE (roe_waa)**：有效范围 [-500, 500]。极端亏损或极低净资产时可能出现较大绝对值，但超过 ±500% 几乎不可能是真实数据。
- **净利率 (netprofit_margin)**：有效范围 [-1000, 1000]。允许较宽范围以容纳微利/微营收公司。
- **资产负债率 (debt_to_assets)**：有效范围 [0, 300]。负债可以超过资产（资不抵债），但 300% 以上几乎不可能。

#### Scenario: 毛利率异常（真实案例：44,969,179.57%）

- **WHEN** `ValuationSnapshotBuilderImpl.build()` 被调用，且 `latest_finance.gross_margin` 的值为 `44969179.57`（超出 [-100, 100] 范围）
- **THEN** `ValuationSnapshotDTO.gros_profit_margin` SHALL 为 `"N/A"`，且记录 WARNING 日志说明毛利率值异常

#### Scenario: ROE 异常

- **WHEN** `ValuationSnapshotBuilderImpl.build()` 被调用，且 `latest_finance.roe_waa` 的值超出 [-500, 500] 范围
- **THEN** `ValuationSnapshotDTO.roe` SHALL 为 `"N/A"`，且记录 WARNING 日志说明 ROE 值异常

#### Scenario: 净利率异常

- **WHEN** `ValuationSnapshotBuilderImpl.build()` 被调用，且 `latest_finance.netprofit_margin` 的值超出 [-1000, 1000] 范围
- **THEN** `ValuationSnapshotDTO.net_profit_margin` SHALL 为 `"N/A"`，且记录 WARNING 日志

#### Scenario: 资产负债率异常

- **WHEN** `ValuationSnapshotBuilderImpl.build()` 被调用，且 `latest_finance.debt_to_assets` 的值超出 [0, 300] 范围
- **THEN** `ValuationSnapshotDTO.debt_to_assets` SHALL 为 `"N/A"`，且记录 WARNING 日志

#### Scenario: 所有指标在合理范围内

- **WHEN** `ValuationSnapshotBuilderImpl.build()` 被调用，且所有财务指标均在合理范围内
- **THEN** 行为与当前一致，正常填入数值，无额外 WARNING 日志

---

### Requirement: 毛利率趋势计算防御异常基础值

`_calculate_gross_margin_trend()` 在比较两期毛利率时，SHALL 先校验两期基础值是否均在合理范围内（[-100, 100]）。若任一基础值超出范围，趋势计算 SHALL 返回 `"N/A"` 而非产生荒谬的趋势描述（如"同比上升 5,502,560.9%"）。

#### Scenario: 基础值异常导致趋势无效

- **WHEN** `_calculate_gross_margin_trend()` 被调用，且最新期 `gross_margin` 为 `44969179.57`（超出合理范围）
- **THEN** 函数 SHALL 返回 `"N/A"`，不输出误导性的趋势描述

#### Scenario: 两期均在合理范围内

- **WHEN** `_calculate_gross_margin_trend()` 被调用，且最新期和上一期 `gross_margin` 均在 [-100, 100] 范围内
- **THEN** 行为与当前一致，正常计算同比趋势

#### Scenario: 仅一期异常

- **WHEN** `_calculate_gross_margin_trend()` 被调用，最新期 `gross_margin` 在合理范围内，但上一期超出范围（或反之）
- **THEN** 函数 SHALL 返回 `"N/A"`

---

### Requirement: 合理性阈值集中定义

所有财务指标的合理性阈值 SHALL 以模块级常量形式集中定义在 `ValuationSnapshotBuilderImpl` 所在模块中（`infrastructure/valuation_snapshot/snapshot_builder.py`），便于后续根据业务需求调整。不使用魔数。

#### Scenario: 阈值可追溯

- **WHEN** 开发者需要调整某个指标的合理性阈值
- **THEN** 仅需修改 `snapshot_builder.py` 中对应的常量定义，无需全文搜索魔数

---

## capability: adapter-null-safety

> Source: adapter-null-safety/spec.md (archived)

修复数据适配器层的空值崩溃风险：对 `StockBasicInfoDTO.daily` 做 `None` 防护，收窄异常捕获范围，统一 `third_code` 取值来源。受影响的适配器：ValuationDataAdapter、MacroDataAdapter、CatalystDataAdapter。

---

## Requirements

### Requirement: Adapter 层 daily 空值防护

当 `GetStockBasicInfoUseCase` 返回的 `StockBasicInfoDTO.daily` 为 `None` 时（标的存在但无最新日线数据），数据适配器 SHALL 返回 `None`（表示"数据不可用"），而非抛出 `AttributeError`。
受影响的适配器：`ValuationDataAdapter`、`MacroDataAdapter`。

#### Scenario: 估值适配器遇到 daily 为 None

- **WHEN** `ValuationDataAdapter.get_stock_overview(symbol)` 被调用，且 `GetStockBasicInfoUseCase` 返回的 `StockBasicInfoDTO` 中 `daily` 为 `None`
- **THEN** 方法 SHALL 返回 `None`，且记录 WARNING 级别日志说明该标的缺少日线数据

#### Scenario: 宏观适配器遇到 daily 为 None

- **WHEN** `MacroDataAdapter.get_stock_overview(symbol)` 被调用，且 `GetStockBasicInfoUseCase` 返回的 `StockBasicInfoDTO` 中 `daily` 为 `None`
- **THEN** 方法 SHALL 返回 `None`，且记录 WARNING 级别日志说明该标的缺少日线数据

#### Scenario: daily 正常时行为不变

- **WHEN** `ValuationDataAdapter.get_stock_overview(symbol)` 或 `MacroDataAdapter.get_stock_overview(symbol)` 被调用，且 `daily` 不为 `None`
- **THEN** 方法 SHALL 正常返回 `StockOverviewInput` 或 `MacroStockOverview`，行为与当前一致

---

### Requirement: Catalyst 适配器异常捕获收窄

`CatalystDataAdapter.get_stock_overview()` 的 `except Exception` SHALL 收窄为仅捕获预期的数据查询异常（如 `SQLAlchemyError` 或自定义的数据层异常），非预期异常（如 `TypeError`、`ValueError`、配置错误）SHALL 向上抛出，避免掩盖系统级故障。

#### Scenario: 数据查询异常被优雅处理

- **WHEN** `CatalystDataAdapter.get_stock_overview(symbol)` 内部的 `GetStockBasicInfoUseCase` 抛出数据库连接异常
- **THEN** 方法 SHALL 记录 ERROR 日志并返回 `None`

#### Scenario: 非预期异常不被吞掉

- **WHEN** `CatalystDataAdapter.get_stock_overview(symbol)` 内部发生 `TypeError` 或 `AttributeError` 等编程错误
- **THEN** 异常 SHALL 向上传播，不被 `except` 捕获

---

### Requirement: third_code 取值来源统一

所有数据适配器在构建 stock overview 时，`third_code` 的取值来源 SHALL 统一。当 `daily` 可用时优先从 `daily.third_code` 取值（最新交易日维度），当 `daily` 不可用时回退到 `info.third_code`。

#### Scenario: daily 可用时使用 daily.third_code

- **WHEN** 适配器构建 stock overview 且 `daily` 不为 `None`
- **THEN** `third_code` SHALL 取自 `daily.third_code`

#### Scenario: daily 不可用时回退到 info.third_code

- **WHEN** 适配器构建 stock overview 且 `daily` 为 `None`（本需求仅适用于 Catalyst 适配器，因为估值/宏观适配器在 daily 为 None 时直接返回 None）
- **THEN** `third_code` SHALL 取自 `info.third_code`

---

## capability: indicator-data-sufficiency

> Source: indicator-data-sufficiency/spec.md (archived)

为技术指标计算增加数据量门槛校验，改进数据不足时的标记策略（从误导性默认值改为显式 N/A），确保 LLM 收到的输入可靠。涉及 TechnicalAnalystService、指标计算实现与 Prompt 填充逻辑。

---

## Requirements

### Requirement: 技术分析最低 K 线数量门槛

`TechnicalAnalystService.run()` 在获取日线数据后、计算指标前，SHALL 校验 K 线数量是否满足最低门槛（MIN_BARS_REQUIRED = 30）。不满足时 SHALL 抛出 `BadRequestException` 并给出明确的错误信息，告知用户所需的最低数据量。

#### Scenario: K 线数量充足（≥30 根）

- **WHEN** `TechnicalAnalystService.run()` 获取到 ≥ 30 根 K 线
- **THEN** 正常计算技术指标并调用 Agent，行为与当前一致

#### Scenario: K 线数量不足（<30 根且 >0 根）

- **WHEN** `TechnicalAnalystService.run()` 获取到 1-29 根 K 线
- **THEN** SHALL 抛出 `BadRequestException`，message 中包含实际获取到的 K 线数量和所需的最低数量（30），提示用户同步更多历史数据

#### Scenario: K 线为空（0 根）

- **WHEN** `TechnicalAnalystService.run()` 获取到 0 根 K 线
- **THEN** SHALL 抛出 `BadRequestException`，行为与当前一致（现有的 `if not bars` 检查）

---

### Requirement: 数据不足时指标使用 None 而非误导性默认值

`compute_technical_indicators()` 中，当数据量不足以计算某个指标时，该指标 SHALL 返回 `None`（而非 0.0 或 50.0 等合法但误导性的默认值）。对应的 `TechnicalIndicatorsSnapshot` DTO 中相关字段类型 SHALL 改为 `Optional[float]`。

#### Scenario: RSI 数据不足

- **WHEN** 计算 RSI(14) 但收盘价序列不足 15 根
- **THEN** `rsi_value` SHALL 为 `None`（而非当前的 50.0）

#### Scenario: MACD 数据不足

- **WHEN** 计算 MACD(12,26,9) 但收盘价序列不足 26 根
- **THEN** `macd_dif`、`macd_dea`、`macd_histogram` SHALL 均为 `None`（而非当前的 0.0）

#### Scenario: KDJ 数据不足

- **WHEN** 计算 KDJ(9,3,3) 但数据不足 9 根
- **THEN** `kdj_k`、`kdj_d`、`kdj_j` SHALL 均为 `None`（而非当前的 50.0）

#### Scenario: 布林带数据不足

- **WHEN** 计算布林带(20,2) 但收盘价序列不足 20 根
- **THEN** `bb_upper`、`bb_lower`、`bb_middle`、`bb_bandwidth` SHALL 均为 `None`（而非当前的 0.0）

#### Scenario: 数据充足时行为不变

- **WHEN** 各指标所需的数据量均充足
- **THEN** 指标值 SHALL 为正常计算的浮点数，行为与当前一致

---

### Requirement: Prompt 填充兼容 None 指标值

`fill_user_prompt()` 在填充技术分析 Prompt 模板时，SHALL 将 `None` 值的指标转为字符串 `"N/A"` 后再填入模板，确保 LLM 能明确识别"数据不足"的指标并忽略该条。

#### Scenario: 指标为 None 时填充 N/A

- **WHEN** `snapshot.rsi_value` 为 `None`
- **THEN** Prompt 中 `{rsi_value}` 占位符 SHALL 被替换为 `"N/A"`

#### Scenario: 指标为正常值时行为不变

- **WHEN** `snapshot.rsi_value` 为 `72.5`
- **THEN** Prompt 中 `{rsi_value}` 占位符 SHALL 被替换为 `72.5`，行为与当前一致

---

## capability: concept-data-source

> Source: concept-data-source/spec.md (archived)

data_engineering 模块新增 akshare 概念板块数据能力，包括外部数据获取、PostgreSQL 持久化和对外查询服务，为知识图谱的概念题材维度提供数据底座。

---

## Requirements

### Requirement: Concept 领域实体定义

系统 MUST 在 `data_engineering/domain/model/concept.py` 中定义概念相关领域实体。

`Concept` 实体字段 MUST 包含：

- `code`（str）：概念板块代码（如 `BK0493`），唯一标识
- `name`（str）：概念板块名称（如 "低空经济"）

`ConceptStock` 实体字段 MUST 包含：

- `concept_code`（str）：所属概念板块代码
- `third_code`（str）：股票代码，MUST 为系统标准格式（如 `000001.SZ`）
- `stock_name`（str）：股票名称

#### Scenario: 实体定义在 Domain 层

- **WHEN** 检查 `Concept` 和 `ConceptStock` 的定义位置
- **THEN** MUST 位于 `src/modules/data_engineering/domain/model/concept.py`
- **THEN** 实体 MUST 继承 Pydantic `BaseModel`

---

### Requirement: IConceptDataProvider Port 定义

系统 MUST 在 `data_engineering/domain/ports/providers/concept_data_provider.py` 中定义 `IConceptDataProvider` ABC 接口。

该接口 MUST 包含以下方法：

- `fetch_concept_list() -> list[ConceptInfoDTO]`：获取所有概念板块列表
- `fetch_concept_constituents(symbol: str) -> list[ConceptConstituentDTO]`：获取指定概念板块的成份股列表

方法 MUST 为异步方法（async）。

#### Scenario: Port 在 Domain 层定义

- **WHEN** 检查 `IConceptDataProvider` 的定义位置
- **THEN** 该 ABC 接口 MUST 位于 `src/modules/data_engineering/domain/ports/providers/concept_data_provider.py`
- **THEN** 接口方法的返回类型 MUST 使用 `data_engineering` 领域层定义的 DTO

---

### Requirement: ConceptInfoDTO 定义

系统 MUST 在 `data_engineering` 领域层定义 `ConceptInfoDTO`（Pydantic BaseModel），用于表示概念板块基本信息。

字段 MUST 包含：

- `code`（str）：概念板块代码（如 `BK0493`）
- `name`（str）：概念板块名称（如 "低空经济"）

#### Scenario: DTO 字段完整

- **WHEN** 从 akshare 获取概念列表并转换为 `ConceptInfoDTO`
- **THEN** 每条记录 MUST 包含非空的 `code` 和 `name`

#### Scenario: 空值过滤

- **WHEN** akshare 返回的某条记录 `code` 或 `name` 为空
- **THEN** 该记录 MUST 被过滤掉，不包含在返回结果中

---

### Requirement: ConceptConstituentDTO 定义

系统 MUST 在 `data_engineering` 领域层定义 `ConceptConstituentDTO`（Pydantic BaseModel），用于表示概念板块的成份股。

字段 MUST 包含：

- `stock_code`（str）：股票代码，MUST 为系统标准的 `third_code` 格式（如 `000001.SZ`）
- `stock_name`（str）：股票名称

#### Scenario: 深交所股票代码转换

- **WHEN** akshare 返回的原始股票代码为 `000001`（`0` 开头）
- **THEN** `ConceptConstituentDTO.stock_code` MUST 为 `000001.SZ`

#### Scenario: 上交所股票代码转换

- **WHEN** akshare 返回的原始股票代码以 `6` 开头（如 `601398`）
- **THEN** `stock_code` MUST 为 `601398.SH`

#### Scenario: 创业板股票代码转换

- **WHEN** akshare 返回的原始股票代码以 `3` 开头（如 `300750`）
- **THEN** `stock_code` MUST 为 `300750.SZ`

#### Scenario: 科创板股票代码转换

- **WHEN** akshare 返回的原始股票代码以 `68` 开头（如 `688001`）
- **THEN** `stock_code` MUST 为 `688001.SH`

#### Scenario: 北交所股票代码转换

- **WHEN** akshare 返回的原始股票代码以 `4` 或 `8` 开头（如 `430047`、`830799`）
- **THEN** `stock_code` MUST 为 `430047.BJ` 或 `830799.BJ`

---

### Requirement: AkShareConceptClient 实现

系统 MUST 在 `data_engineering/infrastructure/external_apis/akshare/` 下实现 `AkShareConceptClient`，实现 `IConceptDataProvider` 接口。

实现 MUST 满足以下约束：

- 调用 akshare 的 `stock_board_concept_name_em()` 获取概念列表
- 调用 akshare 的 `stock_board_concept_cons_em(symbol=<概念名称>)` 获取成份股
- akshare API 为同步调用，MUST 通过 `run_in_executor` 包装为异步方法
- 请求间 MUST 有可配置的间隔（默认 0.3s），避免触发限流
- 股票代码格式转换 MUST 在此 Adapter 内完成，对上层透明

#### Scenario: 获取概念列表

- **WHEN** 调用 `fetch_concept_list()`
- **THEN** 返回包含所有概念板块的 `list[ConceptInfoDTO]`
- **THEN** 列表 MUST 不为空（东方财富概念板块通常有 300+ 个）

#### Scenario: 获取概念成份股

- **WHEN** 调用 `fetch_concept_constituents(symbol="低空经济")`
- **THEN** 返回该概念下所有成份股的 `list[ConceptConstituentDTO]`
- **THEN** 每条记录的 `stock_code` MUST 为标准 `third_code` 格式

#### Scenario: API 调用失败时抛出领域异常

- **WHEN** akshare API 调用因网络错误或限流失败
- **THEN** MUST 抛出继承自 `AppException` 的领域异常
- **THEN** 异常信息 MUST 包含失败的 API 名称和原始错误描述

#### Scenario: 请求间隔控制

- **WHEN** 连续调用 `fetch_concept_constituents()` 多次
- **THEN** 每次调用之间 MUST 至少间隔配置的时间（默认 0.3s）

---

### Requirement: IConceptRepository Port 定义

系统 MUST 在 `data_engineering/domain/ports/repositories/concept_repo.py` 中定义 `IConceptRepository` ABC 接口。

该接口 MUST 包含以下方法：

- `upsert_concepts(concepts: list[Concept]) -> int`：批量 UPSERT 概念记录（by code），返回影响行数
- `replace_all_concept_stocks(mappings: list[ConceptStock]) -> int`：全量替换 `concept_stock` 表（先清后建），返回插入行数
- `get_all_concepts() -> list[Concept]`：查询所有概念记录
- `get_concept_stocks(concept_code: str) -> list[ConceptStock]`：查询指定概念的成份股
- `get_all_concepts_with_stocks() -> list[ConceptWithStocksDTO]`：查询所有概念及其成份股（聚合查询，供 KC 适配器使用）

方法 MUST 为异步方法（async）。

#### Scenario: Port 在 Domain 层定义

- **WHEN** 检查 `IConceptRepository` 的定义位置
- **THEN** 该 ABC 接口 MUST 位于 `src/modules/data_engineering/domain/ports/repositories/concept_repo.py`

#### Scenario: upsert_concepts 幂等写入

- **WHEN** 对同一 `code` 的概念执行两次 `upsert_concepts`
- **THEN** PostgreSQL 中仅存在一条该 `code` 的记录，`name` 和 `updated_at` 为最新值

#### Scenario: replace_all_concept_stocks 全量替换

- **WHEN** 调用 `replace_all_concept_stocks` 传入新的映射列表
- **THEN** `concept_stock` 表中的旧数据 MUST 被全部清除
- **THEN** 新数据 MUST 全部插入

---

### Requirement: ConceptWithStocksDTO 定义

系统 MUST 定义 `ConceptWithStocksDTO`（Pydantic BaseModel），用于聚合查询返回概念及其成份股。

字段 MUST 包含：

- `code`（str）：概念板块代码
- `name`（str）：概念板块名称
- `stocks`（list[ConceptStock]）：该概念下的成份股列表

#### Scenario: 聚合查询结果完整

- **WHEN** 调用 `get_all_concepts_with_stocks()` 且数据库中有概念数据
- **THEN** 每条 `ConceptWithStocksDTO` MUST 包含对应概念的所有成份股

---

### Requirement: PostgreSQL 持久化实现

系统 MUST 在 `data_engineering/infrastructure/persistence/` 下实现概念数据的 PostgreSQL 持久化。

包含：

- ORM Model：`ConceptModel`（映射 `concept` 表）和 `ConceptStockModel`（映射 `concept_stock` 表）
- Repository 实现：`PgConceptRepository`，实现 `IConceptRepository` 接口
- Alembic Migration：创建 `concept` 和 `concept_stock` 表

`concept` 表 MUST 包含：`id`（PK）、`code`（UNIQUE）、`name`、`created_at`、`updated_at`。

`concept_stock` 表 MUST 包含：`id`（PK）、`concept_code`、`third_code`、`stock_name`、`created_at`，并在 `(concept_code, third_code)` 上建立唯一约束。

#### Scenario: 数据库表创建

- **WHEN** 运行 Alembic migration
- **THEN** PostgreSQL 中 MUST 存在 `concept` 和 `concept_stock` 两张表

#### Scenario: 唯一约束生效

- **WHEN** 尝试插入重复的 `(concept_code, third_code)` 到 `concept_stock` 表
- **THEN** MUST 触发唯一约束冲突

---

### Requirement: SyncConceptDataCmd 同步命令

系统 MUST 在 `data_engineering/application/commands/` 下实现 `SyncConceptDataCmd`，负责从 akshare 获取概念数据并写入 PostgreSQL。

同步流程 MUST 包含：

1. 调用 `IConceptDataProvider.fetch_concept_list()` 获取所有概念
2. 对每个概念，调用 `fetch_concept_constituents(symbol)` 获取成份股（逐概念错误隔离）
3. 调用 `IConceptRepository.upsert_concepts()` 写入概念记录
4. 调用 `IConceptRepository.replace_all_concept_stocks()` 全量替换成份股映射

#### Scenario: 首次概念数据同步

- **WHEN** 触发概念数据同步且 PostgreSQL 中无概念数据
- **THEN** 从 akshare 获取所有概念及成份股并写入 PostgreSQL
- **THEN** `concept` 表记录数 MUST 等于成功获取的概念数
- **THEN** `concept_stock` 表记录数 MUST 等于所有概念成份股的总和

#### Scenario: 重复同步保持最新

- **WHEN** 再次触发概念数据同步
- **THEN** `concept` 表通过 UPSERT 更新（名称变更被捕获）
- **THEN** `concept_stock` 表全量替换为最新数据

#### Scenario: 部分概念获取失败不中断

- **WHEN** 获取某个概念的成份股时 akshare API 失败
- **THEN** 该概念的错误 MUST 被记录到日志（ERROR 级别）
- **THEN** 其余概念的同步 MUST 正常继续
- **THEN** 已成功获取的概念和成份股数据 MUST 被写入 PostgreSQL

#### Scenario: 同步完成后报告结果

- **WHEN** 同步命令执行完毕
- **THEN** MUST 返回结果摘要：概念总数、成功数、失败数、成份股总数、总耗时

---

### Requirement: DI Container 注册

`DataEngineeringContainer` MUST 注册以下实现并对外暴露：

- `AkShareConceptClient` 作为 `IConceptDataProvider` 的实现
- `PgConceptRepository` 作为 `IConceptRepository` 的实现
- `SyncConceptDataCmd` 应用命令
- 提供 `IConceptRepository` 实例供其他模块（KC）通过适配器访问

#### Scenario: 依赖注入可用

- **WHEN** 通过 DI 容器请求 `IConceptDataProvider` 实例
- **THEN** MUST 返回 `AkShareConceptClient` 实例

#### Scenario: Repository 可注入

- **WHEN** 通过 DI 容器请求 `IConceptRepository` 实例
- **THEN** MUST 返回 `PgConceptRepository` 实例

---

## capability: capital-flow-analysis

> Source: capital-flow-analysis/spec.md (archived)

市场主力资金行为分析能力，涵盖龙虎榜数据解析（机构/游资席位净买卖）、板块/个股维度的资金净流入估算，为超短线交易提供资金流向洞察。

---

## Requirements

### Requirement: ICapitalFlowDataPort 接口定义

系统 MUST 在 `market_insight/domain/ports/capital_flow_data_port.py` 中定义 `ICapitalFlowDataPort` ABC 接口，用于从 `data_engineering` 消费资金行为数据。

该接口 MUST 包含以下方法：

- `get_dragon_tiger(trade_date: date) -> list[DragonTigerItemDTO]`：获取指定日期的龙虎榜详情
- `get_sector_capital_flow(trade_date: date, sector_type: str | None = None) -> list[SectorCapitalFlowItemDTO]`：获取指定日期的板块资金流向

所有方法 MUST 为异步方法（async）。

`DragonTigerItemDTO` 字段 MUST 包含：
- `third_code`（str）、`stock_name`（str）、`pct_chg`（float）、`close`（float）
- `reason`（str）：上榜原因
- `net_amount`（float）：净买入额
- `buy_amount`（float）：买入总额
- `sell_amount`（float）：卖出总额
- `buy_seats`（list[dict]）：买入席位详情
- `sell_seats`（list[dict]）：卖出席位详情

`SectorCapitalFlowItemDTO` 字段 MUST 包含：
- `sector_name`（str）：板块名称
- `sector_type`（str）：板块类型
- `net_amount`（float）：净流入额（万元）
- `inflow_amount`（float）：流入额（万元）
- `outflow_amount`（float）：流出额（万元）
- `pct_chg`（float）：板块涨跌幅

DTO MUST 定义在 `market_insight/domain/dtos/capital_flow_dtos.py` 中，不直接引用 `data_engineering` 的类型。

#### Scenario: Port 在 Market Insight Domain 层定义

- **WHEN** 检查 `ICapitalFlowDataPort` 的定义位置
- **THEN** MUST 位于 `market_insight/domain/ports/capital_flow_data_port.py`
- **THEN** 返回类型 MUST 使用 `market_insight` 领域层 DTO

---

### Requirement: DeCapitalFlowDataAdapter 适配器实现

系统 MUST 在 `market_insight/infrastructure/adapters/de_capital_flow_data_adapter.py` 中实现 `DeCapitalFlowDataAdapter`，实现 `ICapitalFlowDataPort` 接口。

该适配器 MUST 通过 `DataEngineeringContainer` 获取以下查询用例并调用：
- `GetDragonTigerByDateUseCase` → 转换为 `DragonTigerItemDTO`
- `GetSectorCapitalFlowByDateUseCase` → 转换为 `SectorCapitalFlowItemDTO`

MUST 将 `data_engineering` 的领域实体转换为 `market_insight` 的领域层 DTO。

#### Scenario: 正常获取龙虎榜数据

- **WHEN** 调用 `get_dragon_tiger(date(2024, 2, 15))`
- **THEN** 系统 MUST 通过 DE 查询用例获取数据并转换为 `list[DragonTigerItemDTO]`

#### Scenario: DE 查询无数据

- **WHEN** 调用 `get_dragon_tiger` 但 DE 中无对应日期数据
- **THEN** 系统 MUST 返回空列表

---

### Requirement: CapitalFlowAnalyzer 领域服务

系统 MUST 在 `market_insight/domain/services/capital_flow_analyzer.py` 中实现 `CapitalFlowAnalyzer` 领域服务。

该服务 MUST 提供以下方法：

1. `analyze_dragon_tiger(dragon_tiger_data: list[DragonTigerItemDTO]) -> DragonTigerAnalysis`

   分析龙虎榜数据。`DragonTigerAnalysis` 字段 MUST 包含：
   - `total_count`（int）：上榜股票总数
   - `net_buy_count`（int）：净买入股票数
   - `net_sell_count`（int）：净卖出股票数
   - `total_net_amount`（float）：净买入总额
   - `institution_net_amount`（float）：机构席位净买入额
   - `hot_money_net_amount`（float）：游资席位净买入额
   - `top_net_buys`（list[DragonTigerStockSummary]）：净买入前 5 名
   - `top_net_sells`（list[DragonTigerStockSummary]）：净卖出前 5 名

   `DragonTigerStockSummary` 字段 MUST 包含：
   - `third_code`（str）：股票代码
   - `stock_name`（str）：股票名称
   - `net_amount`（float）：净买入额
   - `reason`（str）：上榜原因

2. `analyze_sector_capital_flow(sector_flow_data: list[SectorCapitalFlowItemDTO]) -> SectorCapitalFlowAnalysis`

   分析板块资金流向。`SectorCapitalFlowAnalysis` 字段 MUST 包含：
   - `total_inflow`（float）：总流入额
   - `total_outflow`（float）：总流出额
   - `net_inflow`（float）：净流入额
   - `net_inflow_sectors`（list[SectorCapitalFlowItemDTO]）：净流入板块列表（按净流入额降序）
   - `net_outflow_sectors`（list[SectorCapitalFlowItemDTO]）：净流出板块列表（按净流出额降序）
   - `top_inflow_sectors`（list[SectorCapitalFlowItemDTO]）：净流入前 10 名
   - `top_outflow_sectors`（list[SectorCapitalFlowItemDTO]）：净流出前 10 名

所有分析方法 MUST 为纯函数式计算，不依赖外部 I/O。

上述结果 DTO MUST 定义在 `market_insight/domain/dtos/capital_flow_dtos.py` 中。

#### Scenario: 龙虎榜分析正常

- **WHEN** 龙虎榜数据包含 10 只股票，其中 6 只净买入、4 只净卖出，机构席位净买入 5000 万，游资席位净卖出 2000 万
- **THEN** `total_count` MUST 为 10，`net_buy_count` 为 6，`net_sell_count` 为 4，`institution_net_amount` 为 50000000.0，`hot_money_net_amount` 为 -20000000.0

#### Scenario: 机构席位识别

- **WHEN** 龙虎榜买入席位包含"机构专用"、"机构专用1"等名称
- **THEN** 这些席位 MUST 被识别为机构席位，计入 `institution_net_amount`

#### Scenario: 龙虎榜为空

- **WHEN** 龙虎榜数据为空列表
- **THEN** `total_count` 为 0，`total_net_amount` 为 0.0，`top_net_buys` 和 `top_net_sells` 为空列表

#### Scenario: 板块资金流向排名

- **WHEN** 板块资金流向数据包含 20 个板块，其中 12 个净流入、8 个净流出
- **THEN** `net_inflow_sectors` MUST 包含 12 个板块，`net_outflow_sectors` MUST 包含 8 个板块，`top_inflow_sectors` MUST 包含净流入前 10 名

#### Scenario: 资金流向为空

- **WHEN** 板块资金流向数据为空列表
- **THEN** `total_inflow`、`total_outflow`、`net_inflow` 均为 0.0，所有列表字段为空

#### Scenario: 机构游资席位分类

- **WHEN** 席位名称包含"机构"、"社保"、"基金"等关键词
- **THEN** 这些席位 MUST 被归类为机构席位
- **WHEN** 席位名称包含"营业部"、"证券"、"游资"等关键词
- **THEN** 这些席位 MUST 被归类为游资席位

#### Scenario: 龙虎榜汇总计算

- **WHEN** 计算龙虎榜汇总数据
- **THEN** `total_net_amount` MUST 等于所有股票 `net_amount` 的总和
- **THEN** `institution_net_amount` MUST 等于所有机构席位的净买卖差额
- **THEN** `hot_money_net_amount` MUST 等于所有游资席位的净买卖差额

#### Scenario: 板块资金流向汇总

- **WHEN** 计算板块资金流向汇总
- **THEN** `total_inflow` MUST 等于所有板块 `inflow_amount` 的总和
- **THEN** `total_outflow` MUST 等于所有板块 `outflow_amount` 的总和
- **THEN** `net_inflow` MUST 等于 `total_inflow - total_outflow`

---

### Requirement: GetCapitalFlowAnalysisQuery 查询用例

系统 MUST 在 `market_insight/application/queries/get_capital_flow_analysis_query.py` 中实现 `GetCapitalFlowAnalysisQuery`。

接口签名：
```
execute(trade_date: date, sector_type: str | None = None) -> CapitalFlowAnalysisDTO
```

该用例 MUST：
1. 通过 `ICapitalFlowDataPort` 获取龙虎榜和板块资金流向数据
2. 调用 `CapitalFlowAnalyzer` 计算各项分析指标
3. 组装并返回 `CapitalFlowAnalysisDTO`

`CapitalFlowAnalysisDTO` 为 Application 层 DTO，字段 MUST 包含：
- `trade_date`（date）
- `dragon_tiger_analysis`（DragonTigerAnalysisDTO）：龙虎榜分析
- `sector_capital_flow_analysis`（SectorCapitalFlowAnalysisDTO）：板块资金流向分析

Application 层 DTO MUST 定义在 `market_insight/application/dtos/capital_flow_analysis_dtos.py` 中。

#### Scenario: 正常查询资金流向分析

- **WHEN** 调用 `execute(date(2024, 2, 15))`，DE 中存在对应数据
- **THEN** 系统 MUST 返回包含龙虎榜和板块资金流向分析的 `CapitalFlowAnalysisDTO`

#### Scenario: 部分数据缺失

- **WHEN** 调用 `execute`，龙虎榜有数据但板块资金流向无数据
- **THEN** 系统 MUST 正常返回结果，板块资金流向分析中各字段为默认值

#### Scenario: 按板块类型过滤

- **WHEN** 调用 `execute(date(2024, 2, 15), sector_type="概念资金流")`
- **THEN** 系统 MUST 在板块资金流向分析中仅包含"概念资金流"类型的数据

---

## Best Practices Checklist

### YAML Frontmatter
- [x] 包含 `title`：模块规格标题
- [x] 包含 `version`：版本号
- [x] 包含 `last_updated`：最后更新日期（YYYY-MM-DD）
- [x] 包含 `module`：模块名称
- [x] 包含 `capabilities`：能力列表
- [x] 包含 `source_specs`：原始 spec 来源列表（如适用）

### Document Structure
- [x] 有 `## Purpose` 部分：模块目的概述
- [x] 有 `## Capabilities` 部分：能力列表表格
- [x] 有 `## General Conventions` 部分：通用约定
- [x] 每个 capability 有来源注释：`> Source: ...`
- [x] 使用 `---` 分隔不同的 capability

### Content Guidelines
- [x] 使用 `## Requirements` 而非 `## ADDED Requirements`（归档后的主 spec）
- [x] 所有需求标题使用 `### Requirement:` 前缀
- [x] 所有场景标题使用 `#### Scenario:` 前缀
- [x] 场景使用 **WHEN** / **THEN** 格式
- [x] 使用一致的需求语言（SHALL/MUST/SHOULD/MAY）
- [x] 中文注释和文档字符串

### Readability
- [x] 标题清晰、描述性强
- [x] 表格格式规范对齐
- [x] 代码块有语言标识
- [x] 长文件考虑添加目录（TOC）

### Maintenance
- [x] 更新 `last_updated` 日期
- [x] 保持 `version` 号同步
- [x] 记录 `source_specs` 便于追溯

---

## capability: market-data-sync-api

> Source: market-data-sync-api/spec.md (archived)

`market-data-sync-api` 能力为 `data_engineering` 模块提供 HTTP API 接口，允许通过 HTTP 请求触发市场行情数据和概念数据的同步操作。

---

## Requirements

### Requirement: Market Router 创建

系统 SHALL 在 `src/modules/data_engineering/presentation/rest/market_router.py` 中创建 FastAPI 路由模块，提供市场数据同步接口。

该路由 SHALL 使用 prefix `/data-engineering/market`，tag 为 `Market Data Sync`。

#### Scenario: 路由文件创建
- **WHEN** 检查 `data_engineering/presentation/rest/` 目录
- **THEN**  SHALL 存在 `market_router.py` 文件
- **THEN** 该文件 SHALL 定义 `APIRouter` 实例，prefix 为 `/data-engineering/market`

---

### Requirement: 依赖注入容器

系统 SHALL 在 `market_router.py` 中定义依赖注入函数，通过 `DataEngineeringContainer` 获取 Command 实例。

该函数 SHALL 接受 `AsyncSession` 依赖，返回 `DataEngineeringContainer` 实例。

#### Scenario: 容器依赖注入
- **WHEN** 检查 `market_router.py` 中的依赖注入函数
- **THEN**  SHALL 存在 `get_container` 函数
- **THEN** 该函数 SHALL 使用 `Depends(get_db_session)` 获取数据库会话
- **THEN** 该函数 SHALL 返回 `DataEngineeringContainer(session)` 实例

---

### Requirement: AkShare 统一同步接口

系统 SHALL 提供 `POST /api/data-engineering/market/sync/akshare` 接口，用于统一同步5个市场数据。

该接口 SHALL：
- 接受可选查询参数 `trade_date`（格式：YYYY-MM-DD），默认为当天
- 调用 `SyncAkShareMarketDataCmd.execute(trade_date)`
- 返回 `BaseResponse[AkShareSyncResult]` 格式响应

#### Scenario: 统一同步成功
- **WHEN** 客户端调用 `POST /api/data-engineering/market/sync/akshare`
- **THEN** 系统 SHALL 调用 `SyncAkShareMarketDataCmd` 执行同步
- **THEN** 系统 SHALL 返回包含 `AkShareSyncResult` 的成功响应

#### Scenario: 指定日期同步
- **WHEN** 客户端调用 `POST /api/data-engineering/market/sync/akshare?trade_date=2026-02-18`
- **THEN** 系统 SHALL 使用指定日期 `2026-02-18` 执行同步

---

### Requirement: 涨停池同步接口

系统 SHALL 提供 `POST /api/data-engineering/market/sync/limit-up-pool` 接口，用于单独同步涨停池数据。

该接口 SHALL：
- 接受可选查询参数 `trade_date`（格式：YYYY-MM-DD），默认为当天
- 调用 `SyncLimitUpPoolCmd.execute(trade_date)`
- 返回 `BaseResponse` 格式响应，包含 `count` 和 `message` 字段

#### Scenario: 涨停池同步成功
- **WHEN** 客户端调用 `POST /api/data-engineering/market/sync/limit-up-pool`
- **THEN** 系统 SHALL 调用 `SyncLimitUpPoolCmd` 执行同步
- **THEN** 系统 SHALL 返回包含同步条数的成功响应

---

### Requirement: 炸板池同步接口

系统 SHALL 提供 `POST /api/data-engineering/market/sync/broken-board` 接口，用于单独同步炸板池数据。

该接口 SHALL：
- 接受可选查询参数 `trade_date`（格式：YYYY-MM-DD），默认为当天
- 调用 `SyncBrokenBoardCmd.execute(trade_date)`
- 返回 `BaseResponse` 格式响应，包含 `count` 和 `message` 字段

#### Scenario: 炸板池同步成功
- **WHEN** 客户端调用 `POST /api/data-engineering/market/sync/broken-board`
- **THEN** 系统 SHALL 调用 `SyncBrokenBoardCmd` 执行同步
- **THEN** 系统 SHALL 返回包含同步条数的成功响应

---

### Requirement: 昨日涨停同步接口

系统 SHALL 提供 `POST /api/data-engineering/market/sync/previous-limit-up` 接口，用于单独同步昨日涨停表现数据。

该接口 SHALL：
- 接受可选查询参数 `trade_date`（格式：YYYY-MM-DD），默认为当天
- 调用 `SyncPreviousLimitUpCmd.execute(trade_date)`
- 返回 `BaseResponse` 格式响应，包含 `count` 和 `message` 字段

#### Scenario: 昨日涨停同步成功
- **WHEN** 客户端调用 `POST /api/data-engineering/market/sync/previous-limit-up`
- **THEN** 系统 SHALL 调用 `SyncPreviousLimitUpCmd` 执行同步
- **THEN** 系统 SHALL 返回包含同步条数的成功响应

---

### Requirement: 龙虎榜同步接口

系统 SHALL 提供 `POST /api/data-engineering/market/sync/dragon-tiger` 接口，用于单独同步龙虎榜数据。

该接口 SHALL：
- 接受可选查询参数 `trade_date`（格式：YYYY-MM-DD），默认为当天
- 调用 `SyncDragonTigerCmd.execute(trade_date)`
- 返回 `BaseResponse` 格式响应，包含 `count` 和 `message` 字段

#### Scenario: 龙虎榜同步成功
- **WHEN** 客户端调用 `POST /api/data-engineering/market/sync/dragon-tiger`
- **THEN** 系统 SHALL 调用 `SyncDragonTigerCmd` 执行同步
- **THEN** 系统 SHALL 返回包含同步条数的成功响应

---

### Requirement: 板块资金流向同步接口

系统 SHALL 提供 `POST /api/data-engineering/market/sync/sector-capital-flow` 接口，用于单独同步板块资金流向数据。

该接口 SHALL：
- 接受可选查询参数 `trade_date`（格式：YYYY-MM-DD），默认为当天
- 调用 `SyncSectorCapitalFlowCmd.execute(trade_date)`
- 返回 `BaseResponse` 格式响应，包含 `count` 和 `message` 字段

#### Scenario: 板块资金流向同步成功
- **WHEN** 客户端调用 `POST /api/data-engineering/market/sync/sector-capital-flow`
- **THEN** 系统 SHALL 调用 `SyncSectorCapitalFlowCmd` 执行同步
- **THEN** 系统 SHALL 返回包含同步条数的成功响应

---

### Requirement: 概念数据同步接口

系统 SHALL 提供 `POST /api/data-engineering/market/sync/concept` 接口，用于同步概念数据。

该接口 SHALL：
- 无需查询参数
- 调用 `SyncConceptDataCmd.execute()`
- 返回 `BaseResponse[ConceptSyncResult]` 格式响应

#### Scenario: 概念数据同步成功
- **WHEN** 客户端调用 `POST /api/data-engineering/market/sync/concept`
- **THEN** 系统 SHALL 调用 `SyncConceptDataCmd` 执行同步
- **THEN** 系统 SHALL 返回包含 `ConceptSyncResult` 的成功响应

---

### Requirement: 路由注册

系统 SHALL 将 `market_router` 注册到主 FastAPI 应用中。

#### Scenario: 路由已注册
- **WHEN** 检查主应用路由注册
- **THEN** `market_router` SHALL 已被包含在应用路由中
