# Spec: de-clean-arch-refactor

data_engineering 模块整洁架构合规重构：Presentation 层瘦身、Application 层服务化、Command 拆分与命名统一、DTO 合规整改、领域建模修正、返回值类型化、历史同步触发方式变更、日志与注释清理。

**测试约定**：每个 `#### Scenario:` 在变更**交付时**须对应至少一个自动化测试用例（单元或集成）；实现顺序可先实现再补测，以完整测试通过为需求完成标准。

---

## CHANGED Requirements

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

## ADDED Requirements

### Requirement: DataSyncApplicationService

系统 SHALL 在 `application/services/` 下新增 `DataSyncApplicationService`，作为所有数据同步任务的统一编排入口。该服务 SHALL 封装 session 管理、Container/Factory 获取、ExecutionTracker 集成等逻辑，对外暴露简洁的异步方法供 Presentation 层调用。

#### Scenario: Service 提供所有同步入口

- **WHEN** 审查 `DataSyncApplicationService` 的公开方法
- **THEN** SHALL 包含以下方法：`run_daily_incremental_sync`、`run_incremental_finance_sync`、`run_concept_sync`、`run_akshare_market_data_sync`、`run_stock_basic_sync`、`run_daily_history_sync`、`run_finance_history_sync`

#### Scenario: Service 内部管理 ExecutionTracker

- **WHEN** 通过 `DataSyncApplicationService.run_daily_incremental_sync()` 触发同步
- **THEN** SHALL 自动创建 ExecutionTracker 记录执行日志，Presentation 层无需感知

### Requirement: AkShare Query DTO 定义

系统 SHALL 在 `application/dtos/` 下为 AkShare 相关 Query 新增对应 DTO：`LimitUpPoolDTO`、`BrokenBoardDTO`、`DragonTigerDTO`、`PreviousLimitUpDTO`、`SectorCapitalFlowDTO`。DTO 字段 SHALL 为基本类型，与对应 Domain Entity 的对外可见字段一致。

#### Scenario: DTO 字段覆盖 Entity 对外字段

- **WHEN** 审查 `LimitUpPoolDTO` 的字段
- **THEN** SHALL 包含 `trade_date`、`third_code`、`stock_name`、`pct_chg`、`close`、`amount`、`turnover_rate`、`consecutive_boards`、`first_limit_up_time`、`last_limit_up_time`、`industry` 字段
