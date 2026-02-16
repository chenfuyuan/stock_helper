## Context

data_engineering 模块是系统的数据底座，在过去多轮迭代中从最初的 Tushare 数据同步扩展到 AkShare 市场情绪数据、概念板块数据等。增长过程中积累了架构偏离：

- **Presentation 层现状**：`presentation/jobs/sync_scheduler.py`（6 个 job 函数，~184 行）和 `akshare_market_data_jobs.py`（~50 行）承担了 session 管理、Container/Factory 构建、ExecutionTracker 集成等编排职责。Job 函数直接 import `AsyncSessionLocal`、`SchedulerExecutionLogRepository`（Foundation 模块 Infrastructure 层）、`de_config`（本模块 Infrastructure 层）。`stock_routes.py` 的 DI 函数直接构造 `StockRepositoryImpl`、`TushareClient`。
- **命名风格**：`application/commands/` 下 9 个文件中，3 个带 `_cmd.py` 后缀，6 个不带；类名混用 `XXXCmd` 和 `XXXUseCase`；文件名与主类名存在不匹配（如 `sync_daily_bar_cmd.py` → `SyncDailyByDateUseCase`）。
- **`SyncAkShareMarketDataCmd`**：250 行单文件，5 段几乎相同的 fetch→convert→save 逻辑。
- **DTO 违规**：`StockBasicInfoDTO.info: StockInfo` 直接嵌套 Entity；4 个 AkShare Query 直接返回 Entity；`DailyBarDTO` 和 `ConceptSyncResult` 各重复定义 2 次。
- **领域建模**：`SyncTask` 和 `SyncFailureRecord` 用 `@dataclass`，违反 Pydantic 统一约定。
- **返回值**：4 个 Command 返回 `Dict[str, Any]`，2 个返回类型化 dataclass，缺乏一致性。

**约束**：重构为纯行为保持（behavior-preserving），不改变业务逻辑语义；外部消费方（market_insight、research）需同步适配 Query 返回类型变更。

## Goals / Non-Goals

**Goals:**

1. **Presentation 层瘦身**：Job 函数精简为纯入口（调用 Application 服务 → 结束），不包含 session 管理、Container 构建、日期转换等逻辑。
2. **消除跨层/跨模块违规依赖**：Presentation 层不 import Infrastructure 层类；不直接引用其他模块的 Infrastructure 层。
3. **命名统一**：文件名 = 主类名 snake_case；`commands/` 下统一 `_cmd.py` 后缀和 `XXXCmd` 类名。
4. **拆分 `SyncAkShareMarketDataCmd`**：按数据类型拆为独立 Command，消除 God Command。
5. **历史全量同步改为 API 触发**：从 Job Registry 移除，新增 REST 端点。
6. **DTO 合规**：Query 统一返回 DTO；消除重复定义；`StockBasicInfoDTO` 不暴露 Entity。
7. **领域建模统一**：`SyncTask`/`SyncFailureRecord` 迁移为 Pydantic。
8. **返回值类型化**：所有 Command 使用类型化 Result DTO。
9. **日志/注释清理**：统一中文日志；清理遗留注释。

**Non-Goals:**

- 不修改业务逻辑（同步策略、补偿机制、重试逻辑不变）。
- 不修改数据库表结构或 Alembic migration。
- 不重构 Infrastructure 层的 Repository/Provider/Client 实现。
- 不修改 `SyncEngine` 的核心编排算法。
- 不引入新的外部依赖。

## Decisions

### Decision 1: Application 层新增 `DataSyncApplicationService` 承接 Job 编排

**选择**：在 `application/services/` 下新增 `DataSyncApplicationService`，封装所有同步 Job 的编排逻辑（session 创建、Container/Factory 获取、ExecutionTracker 集成、日期转换），对 Presentation 层暴露简单的异步方法。

```python
class DataSyncApplicationService:
    """数据同步应用服务——统一编排所有数据同步任务"""

    async def run_daily_incremental_sync(self, target_date: str | None = None) -> None: ...
    async def run_incremental_finance_sync(self, target_date: str | None = None) -> None: ...
    async def run_concept_sync(self) -> None: ...
    async def run_akshare_market_data_sync(self, target_date: str | None = None) -> None: ...
    async def run_stock_basic_sync(self) -> None: ...
    # 历史全量（仅供 REST API 调用，不注册到调度器）
    async def run_daily_history_sync(self) -> dict: ...
    async def run_finance_history_sync(self) -> dict: ...
```

**替代方案**：在每个 Job 函数内调用 Factory → 编排逻辑仍散落在 Presentation，只是换了位置。

**理由**：Application Service 是自然的编排层；多个触发方式（Job、REST API、CLI）可复用同一个 Service；Presentation 层真正做到"薄入口"。

### Decision 2: ExecutionTracker 集成下沉到 Application 层

**选择**：`DataSyncApplicationService` 内部通过依赖注入获取 `ExecutionTracker`（或其 Port 抽象），Job 函数不再直接 import Foundation 模块的 Infrastructure 类。

**替代方案**：定义 `IExecutionTrackingPort` → 过度抽象，当前只有一个实现，收益不大。

**理由**：ExecutionTracker 是应用层编排关注点（"记录本次执行"），不属于 Presentation；通过 Service 内部管理，Job 函数零依赖跨模块 Infrastructure。后续若需抽象为 Port 可渐进重构。

### Decision 3: 拆分 `SyncAkShareMarketDataCmd` 为独立 Command

**选择**：将 5 类数据同步拆为独立 Command：
- `SyncLimitUpPoolCmd` — 涨停池
- `SyncBrokenBoardCmd` — 炸板池
- `SyncPreviousLimitUpCmd` — 昨日涨停
- `SyncDragonTigerCmd` — 龙虎榜
- `SyncSectorCapitalFlowCmd` — 板块资金流向

原 `SyncAkShareMarketDataCmd` 保留为编排入口，依次调用上述 5 个 Command 并聚合结果。

**替代方案**：用策略模式 + 循环替代手动调用 → 过度工程化，5 类数据差异明显（Provider 不同、Entity 不同），统一接口收益小。

**理由**：每个 Command 单一职责、独立可测；编排入口负责错误隔离和结果聚合；符合 tech-standards 的短函数原则。

### Decision 4: 历史全量同步从调度器移至 REST API

**选择**：
- 从 `job_registry.py` 移除 `sync_daily_history` 和 `sync_history_finance`。
- 在 `presentation/rest/stock_routes.py` 新增 `POST /sync/daily-history` 和 `POST /sync/finance-history` 端点，调用 `DataSyncApplicationService` 的对应方法。
- 这两个端点返回任务 ID，前端可轮询状态。

**替代方案**：保留调度器但设为手动触发 → 调度器语义是"定时"，手动触发不是其职责。

**理由**：历史全量同步是一次性/低频操作（数小时级别），通过 API 触发更合理、更可控；调度器聚焦日常增量同步。

### Decision 5: 命名统一策略

**选择**：

| 当前文件名 | 当前类名 | 重命名后文件名 | 重命名后类名 |
|---|---|---|---|
| `sync_daily_bar_cmd.py` | `SyncDailyByDateUseCase` | `sync_daily_by_date_cmd.py` | `SyncDailyByDateCmd` |
| `sync_daily_history.py` | `SyncDailyHistoryUseCase` | `sync_daily_history_cmd.py` | `SyncDailyHistoryCmd` |
| `sync_finance_cmd.py` | `SyncFinanceHistoryUseCase` | `sync_finance_history_cmd.py` | `SyncFinanceHistoryCmd` |
| `sync_incremental_finance_data.py` | `SyncIncrementalFinanceDataUseCase` | `sync_incremental_finance_cmd.py` | `SyncIncrementalFinanceCmd` |
| `sync_stock_list_cmd.py` | `SyncStocksUseCase` | `sync_stock_list_cmd.py` | `SyncStockListCmd` |

使用 `git mv` 保留 Git 历史。

### Decision 6: DTO 合规——统一提取到 `application/dtos/`

**选择**：
- 将 `DailyBarDTO` 合并为一份（保留 `get_daily_bars_by_date.py` 的版本，含 `third_code` 和 `stock_name`），提取到 `application/dtos/daily_bar_dto.py`。
- 将 `ConceptSyncResult` 提取到 `application/dtos/sync_result_dtos.py`，与其他 Command 的 Result DTO 共存。
- `StockBasicInfoDTO` 改为展开基本类型字段（`third_code`、`symbol`、`name`、`industry` 等），不嵌套 Entity。
- AkShare 相关 Query（涨停池、炸板池、龙虎榜、昨日涨停）新增对应 DTO，Query 返回 DTO 而非 Entity。

**理由**：DTO 被多处 import 时须拆为独立文件（tech-standards）；消除重复定义；确保跨模块接口不暴露 Entity。

### Decision 7: `SyncTask` / `SyncFailureRecord` 迁移为 Pydantic

**选择**：将两个实体从 `@dataclass` 改为继承 `BaseEntity`（Pydantic `BaseModel`）。字段类型和行为方法保持不变，仅基类变更。ORM Model 的 `from_attributes=True` 已配置，无需修改 Repository 映射。

**替代方案**：保持 dataclass 并在 tech-standards 中增加例外 → 增加认知负担，不如统一。

**理由**：tech-standards 明确"实体基类统一使用 Pydantic"；Pydantic 提供统一校验和序列化能力。

### Decision 8: 返回值类型化

**选择**：所有 Command 的返回值改为类型化的 Pydantic DTO（放在 `application/dtos/sync_result_dtos.py`）：

```python
class DailyByDateSyncResult(BaseModel): ...
class DailyHistorySyncResult(BaseModel): ...
class FinanceHistorySyncResult(BaseModel): ...
class IncrementalFinanceSyncResult(BaseModel): ...
class StockListSyncResult(BaseModel): ...
```

消灭所有 `Dict[str, Any]` 返回。

## Risks / Trade-offs

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| **Query 返回类型变更影响下游** | market_insight、research 模块使用 `GetLimitUpPoolByDateUseCase` 等 Query 的代码需适配 DTO | 在 DTO 中保留与 Entity 相同的字段名和类型，下游改动量小；逐模块检查并修复 import |
| **大量文件重命名** | Git diff 可读性降低 | 使用 `git mv` 保留历史；一次原子提交完成所有重命名 |
| **历史同步从调度器移除** | 运维习惯变更 | REST API 端点文档清晰；返回任务 ID 可轮询进度 |
| **`SyncTask` 从 dataclass 迁移 Pydantic** | 行为方法（`start()`、`complete()` 等）中 mutable 操作与 Pydantic 默认 frozen 冲突 | 不设置 `frozen=True`，允许 mutation；或使用 `model_config = ConfigDict(validate_assignment=True)` |

## Open Questions

1. **是否需要为 ExecutionTracker 定义 Port 接口**？当前方案是在 `DataSyncApplicationService` 内部直接使用 Foundation 的 `ExecutionTracker`。若后续有替换需求可再抽象。
2. **`SyncAkShareMarketDataCmd` 拆分后，调度器是否仍注册为一个 Job 还是拆为 5 个独立 Job**？建议保持一个 Job（`sync_akshare_market_data`），内部编排 5 个 Command，保持调度粒度不变。
