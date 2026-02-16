## Why

data_engineering 模块在之前的迭代中逐步增长，积累了多项与 `tech-standards.md` 和 `vision-and-modules.md` 不一致的技术债。核心痛点：

1. **Presentation 层职责越界**：`sync_scheduler.py` 和 `akshare_market_data_jobs.py` 中的 Job 函数不仅做入口调度，还包含 session 管理、Container 构建、日期转换等业务编排逻辑；且直接 import Foundation 模块的 Infrastructure 层类（`ExecutionTracker`、`SchedulerExecutionLogRepository`），违反跨模块只通过 Application 层接口访问的规则。`stock_routes.py` 中的 DI 函数直接构造 `StockRepositoryImpl`、`TushareClient` 等 Infrastructure 类。
2. **文件/类命名风格不统一**：同为 `application/commands/` 下的写操作，有的文件用 `_cmd.py` 后缀（`sync_akshare_market_data_cmd.py`），有的不用（`sync_daily_history.py`、`sync_engine.py`）；类名有的叫 `XXXCmd`，有的叫 `XXXUseCase`。文件名与主类名也存在不匹配（如 `sync_daily_bar_cmd.py` 含 `SyncDailyByDateUseCase`）。
3. **`SyncAkShareMarketDataCmd` 过于臃肿**：单个 Command 包揽涨停池、炸板池、昨日涨停、龙虎榜、板块资金流向共 5 类数据的同步逻辑（~250 行），违反单一职责原则。
4. **Tushare 历史全量同步的触发方式不合理**：日线历史和财务历史的全量同步是一次性/低频操作（数小时级别），不应通过定时调度器触发，更适合通过 REST API 手动触发。
5. **DTO 规范违反**：`StockBasicInfoDTO` 直接嵌套 Domain Entity（`StockInfo`、`StockDaily`）作为字段；`GetLimitUpPoolByDateUseCase` 等 4 个 Query 直接返回 Domain Entity 而非 DTO；`DailyBarDTO` 和 `ConceptSyncResult` 各存在两处重复定义。
6. **领域建模不一致**：`SyncTask` 和 `SyncFailureRecord` 使用 `@dataclass` 而非 Pydantic `BaseModel`，违反 tech-standards 的领域建模约定。
7. **返回值类型不统一**：部分 Command 返回 `Dict[str, Any]`（`SyncDailyHistoryUseCase`、`SyncFinanceHistoryUseCase`），部分返回类型化的 dataclass（`AkShareSyncResult`），缺乏统一标准。
8. **其他杂项**：日志语言中英混用（部分文件用英文日志）；`sync_stock_list_cmd.py` 遗留 debug 注释；`BaseUseCase` 继承关系不一致。

## What Changes

- **Presentation 层瘦身**：Job 函数精简为纯入口（≤10 行），仅调用 Application 层服务；移除对 Infrastructure 层和跨模块 Infrastructure 的直接依赖。
- **Application 层承接业务编排**：新增 `DataSyncApplicationService`，封装所有同步 Job 的编排逻辑（session 管理、ExecutionTracker 集成、Container 构建）。
- **拆分 `SyncAkShareMarketDataCmd`**：按数据类型拆为独立 Command（涨停池、炸板池、昨日涨停、龙虎榜、板块资金流向），原 Command 降级为编排入口。
- **历史全量同步改为接口触发**：将 `sync_daily_history` 和 `sync_history_finance` 从 Job Registry 移除，改为 REST API 端点手动触发。
- **统一文件/类命名**：`application/commands/` 下文件统一使用 `_cmd.py` 后缀，类名统一使用 `XXXCmd` 模式。
- **DTO 合规整改**：`StockBasicInfoDTO` 改为基本类型字段；Query 返回值统一为 DTO；消除重复 DTO 定义，提取到 `application/dtos/`。
- **领域实体迁移到 Pydantic**：`SyncTask` 和 `SyncFailureRecord` 从 dataclass 迁移为 Pydantic BaseModel。
- **统一返回值类型**：所有 Command 使用类型化 Result DTO，消灭 `Dict[str, Any]`。
- **杂项清理**：统一日志语言为中文；清理遗留注释；统一 `BaseUseCase` 继承。

## Capabilities

### New Capabilities

- `de-clean-arch-refactor`: data_engineering 模块整洁架构合规重构——涵盖 Presentation 层瘦身、Application 层服务化、Command 拆分、命名统一、DTO 合规、领域建模修正、返回值类型化、历史同步触发方式变更。

### Modified Capabilities

（无现有 spec 需要修改，本变更为纯重构）

## Impact

- **代码路径**：`src/modules/data_engineering/` 下 `presentation/`、`application/`、`domain/model/` 均涉及改动；重命名约 8 个文件。
- **对外接口**：
  - `application/queries/` 对外暴露的查询接口**签名不变**，但返回类型从 Entity 改为 DTO（消费方需适配）。
  - REST API 新增历史同步触发端点；原有查询端点不变。
  - Job Registry 移除 `sync_daily_history` 和 `sync_history_finance` 两个任务。
- **数据库**：无表结构变更（`SyncTask`/`SyncFailureRecord` 仅代码层面从 dataclass 迁移到 Pydantic，ORM 映射不变）。
- **依赖**：无新增外部依赖。
- **风险**：Query 返回类型变更可能影响 market_insight、research 等下游消费方，需同步适配。
- **验证**：通过自动化测试（单元 + 集成）确认重构后行为不变。
