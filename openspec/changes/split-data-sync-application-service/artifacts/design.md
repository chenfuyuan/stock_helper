# Design: DataSyncApplicationService 拆分方案

## 概述

将臃肿的 `DataSyncApplicationService` 按数据类型拆分为 4 个专门的 Service，同时提取公共模板到基类。

## 目标架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    调用方 (Jobs / REST API)                        │
└─────────────────────────────────────────────────────────────────┘
                                │
                ┌───────────────┼───────────────┐
                ▼               ▼               ▼
        ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
        │ DailySync    │ │ FinanceSync  │ │ MarketData   │
        │ Service      │ │ Service      │ │ SyncService  │
        └──────┬───────┘ └──────┬───────┘ └──────┬───────┘
               │                │                │
               └────────────────┼────────────────┘
                                ▼
                      ┌─────────────────┐
                      │ BasicDataSync   │
                      │ Service         │
                      └────────┬────────┘
                               │
                               ▼
                      ┌─────────────────┐
                      │ SyncServiceBase │
                      │ (公共模板)       │
                      └─────────────────┘
```

## 详细设计

### 1. SyncServiceBase (基类)

**职责**: 封装所有 Service 共有的模板代码（session 管理、ExecutionTracker 集成）

**位置**: `src/modules/data_engineering/application/services/base/sync_service_base.py`

```python
class SyncServiceBase(ABC):
    """数据同步服务基类，封装公共模板代码。"""

    def __init__(self):
        self._logger = logger.bind(service=self.__class__.__name__)

    async def _execute_with_tracking(
        self,
        job_id: str,
        operation: Callable[[], Awaitable[T]],
        success_message: str,
    ) -> T:
        """
        在 ExecutionTracker 的上下文执行操作。

        封装了 session 创建、ExecutionTracker 初始化的模板代码。
        """
        async with AsyncSessionLocal() as session:
            repo = SchedulerExecutionLogRepository(session)
            async with ExecutionTracker(job_id=job_id, repo=repo):
                self._logger.info(f"开始执行: {job_id}")
                result = await operation()
                self._logger.info(success_message)
                return result
```

### 2. DailySyncService

**职责**: 日线数据同步（增量 + 历史）

**位置**: `src/modules/data_engineering/application/services/daily_sync_service.py`

**方法**:
- `run_incremental_sync(target_date: Optional[str]) -> dict` - 日线增量同步
- `run_history_sync() -> SyncTask` - 日线历史全量同步

### 3. FinanceSyncService

**职责**: 财务数据同步（增量 + 历史）

**位置**: `src/modules/data_engineering/application/services/finance_sync_service.py`

**方法**:
- `run_incremental_sync(target_date: Optional[str]) -> IncrementalFinanceSyncResult` - 财务增量同步
- `run_history_sync() -> SyncTask` - 财务历史全量同步

### 4. MarketDataSyncService

**职责**: AkShare 市场数据同步（涨停池、炸板池、龙虎榜等）

**位置**: `src/modules/data_engineering/application/services/market_data_sync_service.py`

**方法**:
- `run_sync(target_date: Optional[str]) -> AkShareSyncResult` - 执行所有市场数据同步

### 5. BasicDataSyncService

**职责**: 基础数据同步（概念、股票基础信息）

**位置**: `src/modules/data_engineering/application/services/basic_data_sync_service.py`

**方法**:
- `run_concept_sync() -> ConceptSyncResult` - 概念数据同步
- `run_stock_basic_sync() -> dict` - 股票基础信息同步

### 6. DataSyncApplicationService (兼容层)

**职责**: 保持向后兼容，方法委托给新的专门 Service

**迁移策略**:
- 第 1 阶段: 保留 `DataSyncApplicationService`，所有方法委托给新 Service
- 第 2 阶段: 逐步更新 Jobs 和 REST API，直接调用新 Service
- 第 3 阶段: 移除 `DataSyncApplicationService`

```python
class DataSyncApplicationService:
    """
    数据同步应用服务（兼容层）。

    所有方法已迁移到专门的 Service。此类仅作为兼容层存在，
    方法委托给新的专门 Service。

    ⚠️ 已弃用：请直接调用 DailySyncService、FinanceSyncService 等专门 Service。
    """

    def __init__(self):
        self._daily_service = DailySyncService()
        self._finance_service = FinanceSyncService()
        self._market_data_service = MarketDataSyncService()
        self._basic_data_service = BasicDataSyncService()

    async def run_daily_incremental_sync(self, target_date: Optional[str] = None) -> dict:
        """委托给 DailySyncService。"""
        return await self._daily_service.run_incremental_sync(target_date)

    # ... 其他方法类似委托
```

## 目录结构变更

```
src/modules/data_engineering/application/services/
├── __init__.py
├── base/                           # 新增: 基类目录
│   ├── __init__.py
│   └── sync_service_base.py        # 新增: 同步服务基类
├── daily_sync_service.py           # 新增: 日线同步服务
├── finance_sync_service.py         # 新增: 财务同步服务
├── market_data_sync_service.py     # 新增: 市场数据同步服务
├── basic_data_sync_service.py      # 新增: 基础数据同步服务
└── data_sync_application_service.py # 修改: 改为兼容层

# Jobs 调用方更新:
src/modules/data_engineering/presentation/jobs/
├── sync_scheduler.py               # 修改: 直接调用新的专门 Service
└── akshare_market_data_jobs.py   # 修改: 直接调用 MarketDataSyncService
```

## 风险评估

| 风险 | 可能性 | 影响 | 缓解措施 |
|------|--------|------|----------|
| 测试用例失效 | 中 | 高 | 保持 `DataSyncApplicationService` 作为兼容层，确保所有现有测试通过后再迁移 |
| 调用方遗漏 | 中 | 高 | 全面搜索 `DataSyncApplicationService` 的引用，确保所有调用方都被更新 |
| 日志/监控中断 | 低 | 中 | 新的 Service 保持相同的日志格式和 job_id 命名规范 |

## 验收标准

- [ ] `SyncServiceBase` 基类创建，包含公共模板代码
- [ ] `DailySyncService` 创建并包含日线相关方法
- [ ] `FinanceSyncService` 创建并包含财务相关方法
- [ ] `MarketDataSyncService` 创建并包含市场数据同步方法
- [ ] `BasicDataSyncService` 创建并包含基础数据同步方法
- [ ] `DataSyncApplicationService` 改为兼容层，方法委托给新 Service
- [ ] `sync_scheduler.py` 更新为直接调用新的专门 Service
- [ ] `akshare_market_data_jobs.py` 更新为直接调用 `MarketDataSyncService`
- [ ] 所有现有测试通过
- [ ] 代码覆盖率不下降
