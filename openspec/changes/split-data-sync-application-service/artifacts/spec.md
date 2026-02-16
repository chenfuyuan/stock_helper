# Spec: DataSyncApplicationService 拆分规格

## 1. SyncServiceBase 基类

### 1.1 功能描述

封装所有数据同步服务共有的模板代码，包括：
- 异步 session 创建和管理
- ExecutionTracker 初始化和使用
- 统一的日志记录格式

### 1.2 接口定义

```python
class SyncServiceBase(ABC):
    """数据同步服务基类。"""

    def __init__(self) -> None:
        """初始化基类，绑定日志记录器。"""
        ...

    @abstractmethod
    def _get_service_name(self) -> str:
        """返回服务名称，用于日志和追踪。"""
        ...

    async def _execute_with_tracking(
        self,
        job_id: str,
        operation: Callable[[], Awaitable[T]],
        success_message: str,
    ) -> T:
        """
        在 ExecutionTracker 上下文中执行操作。

        Args:
            job_id: 任务标识符，用于日志和追踪
            operation: 要执行的异步操作
            success_message: 成功时记录的日志消息

        Returns:
            operation 的返回值

        Raises:
            原样传播 operation 中抛出的异常
        """
        ...
```

### 1.3 行为规格

#### Scenario: 正常执行
- **Given** 调用 `_execute_with_tracking` 方法
- **When** operation 成功完成并返回结果
- **Then**
  - 创建 AsyncSession
  - 初始化 ExecutionTracker
  - 记录开始日志
  - 执行 operation
  - 记录成功日志
  - 返回 operation 的结果

#### Scenario: 异常处理
- **Given** 调用 `_execute_with_tracking` 方法
- **When** operation 抛出异常
- **Then**
  - 异常被原样传播
  - ExecutionTracker 捕获并记录异常
  - 不返回结果

### 1.4 验收标准

- [ ] `SyncServiceBase` 抽象类创建
- [ ] `_execute_with_tracking` 方法封装了 session 和 ExecutionTracker 的模板代码
- [ ] 子类必须实现 `_get_service_name` 抽象方法
- [ ] 日志记录包含服务名称和 job_id
- [ ] 单元测试覆盖正常执行和异常处理场景

---

## 2. DailySyncService

### 2.1 功能描述

负责日线数据的同步，包括：
- 日线增量同步（每日新增数据）
- 日线历史全量同步（初始化或修复时使用）

### 2.2 接口定义

```python
class DailySyncService(SyncServiceBase):
    """日线数据同步服务。"""

    def _get_service_name(self) -> str:
        return "DailySyncService"

    async def run_incremental_sync(
        self,
        target_date: Optional[str] = None
    ) -> dict:
        """
        执行日线增量同步。

        Args:
            target_date: 目标日期 (YYYYMMDD)，默认为当天

        Returns:
            同步结果摘要字典，包含:
            - synced_dates: 同步的日期列表
            - total_count: 同步的总记录数
            - message: 状态消息
        """
        ...

    async def run_history_sync(self) -> SyncTask:
        """
        执行日线历史全量同步。

        Returns:
            SyncTask 对象，包含任务状态和处理记录数
        """
        ...
```

### 2.3 行为规格

#### Scenario: 日线增量同步成功
- **Given** 提供有效的目标日期
- **When** 调用 `run_incremental_sync`
- **Then**
  - 使用 SyncUseCaseFactory 创建同步引擎
  - 执行增量同步
  - 返回包含 synced_dates 和 total_count 的字典

#### Scenario: 日线历史同步成功
- **Given** 无参数调用
- **When** 调用 `run_history_sync`
- **Then**
  - 使用 SyncUseCaseFactory 创建同步引擎
  - 执行历史全量同步
  - 返回 SyncTask 对象

### 2.4 验收标准

- [ ] `DailySyncService` 继承 `SyncServiceBase`
- [ ] `run_incremental_sync` 方法迁移成功
- [ ] `run_history_sync` 方法迁移成功
- [ ] 使用 `_execute_with_tracking` 封装模板代码
- [ ] 单元测试覆盖增量同步和历史同步场景

---

## 3. FinanceSyncService

### 3.1 功能描述

负责财务数据的同步，包括：
- 财务增量同步（每日新增财务数据）
- 财务历史全量同步（初始化或修复时使用）

### 3.2 接口定义

```python
class FinanceSyncService(SyncServiceBase):
    """财务数据同步服务。"""

    def _get_service_name(self) -> str:
        return "FinanceSyncService"

    async def run_incremental_sync(
        self,
        target_date: Optional[str] = None
    ) -> IncrementalFinanceSyncResult:
        """
        执行财务增量同步。

        Args:
            target_date: 目标日期 (YYYYMMDD)，默认为当天

        Returns:
            IncrementalFinanceSyncResult，包含:
            - synced_count: 同步成功的记录数
            - failed_count: 失败的记录数
            - retry_count: 重试次数
            - retry_success_count: 重试成功的次数
            - target_period: 目标同步周期
        """
        ...

    async def run_history_sync(self) -> SyncTask:
        """
        执行财务历史全量同步。

        Returns:
            SyncTask 对象，包含任务状态和处理记录数
        """
        ...
```

### 3.3 行为规格

#### Scenario: 财务增量同步成功
- **Given** 提供有效的目标日期
- **When** 调用 `run_incremental_sync`
- **Then**
  - 使用 SyncUseCaseFactory 创建增量同步用例
  - 执行增量同步
  - 返回 IncrementalFinanceSyncResult

#### Scenario: 财务历史同步成功
- **Given** 无参数调用
- **When** 调用 `run_history_sync`
- **Then**
  - 使用 SyncUseCaseFactory 创建同步引擎
  - 执行历史全量同步
  - 返回 SyncTask 对象

### 3.4 验收标准

- [ ] `FinanceSyncService` 继承 `SyncServiceBase`
- [ ] `run_incremental_sync` 方法迁移成功
- [ ] `run_history_sync` 方法迁移成功
- [ ] 使用 `_execute_with_tracking` 封装模板代码
- [ ] 单元测试覆盖增量同步和历史同步场景

---

## 4. MarketDataSyncService

### 4.1 功能描述

负责 AkShare 市场数据同步，包括：
- 涨停池数据同步
- 炸板池数据同步
- 昨日涨停表现数据同步
- 龙虎榜数据同步
- 板块资金流向数据同步

### 4.2 接口定义

```python
class MarketDataSyncService(SyncServiceBase):
    """AkShare 市场数据同步服务。"""

    def _get_service_name(self) -> str:
        return "MarketDataSyncService"

    async def run_sync(
        self,
        target_date: Optional[str] = None
    ) -> AkShareSyncResult:
        """
        执行 AkShare 市场数据同步。

        依次同步：涨停池、炸板池、昨日涨停、龙虎榜、板块资金流向。
        错误隔离：单个子任务失败不中断其他任务。

        Args:
            target_date: 目标日期 (YYYYMMDD)，默认为当天

        Returns:
            AkShareSyncResult，包含:
            - trade_date: 交易日期
            - limit_up_pool_count: 涨停池记录数
            - broken_board_count: 炸板池记录数
            - previous_limit_up_count: 昨日涨停记录数
            - dragon_tiger_count: 龙虎榜记录数
            - sector_capital_flow_count: 板块资金流向记录数
            - errors: 错误列表
        """
        ...
```

### 4.3 行为规格

#### Scenario: 市场数据同步全部成功
- **Given** 提供有效的目标日期
- **When** 调用 `run_sync`
- **Then**
  - 使用 DataEngineeringContainer 获取 SyncAkShareMarketDataCmd
  - 执行所有 5 个子任务
  - 返回所有记录数都大于 0 的 AkShareSyncResult
  - errors 列表为空

#### Scenario: 部分子任务失败
- **Given** 提供有效的目标日期，但龙虎榜数据源不可用
- **When** 调用 `run_sync`
- **Then**
  - 其他 4 个子任务正常执行
  - 龙虎榜任务失败但不中断其他任务
  - 返回的 AkShareSyncResult 中 dragon_tiger_count = 0
  - errors 列表包含龙虎榜的错误信息

### 4.4 验收标准

- [ ] `MarketDataSyncService` 继承 `SyncServiceBase`
- [ ] `run_sync` 方法迁移成功
- [ ] 使用 `_execute_with_tracking` 封装模板代码
- [ ] 单元测试覆盖全部成功和部分失败场景

---

## 5. BasicDataSyncService

### 5.1 功能描述

负责基础数据同步，包括：
- 概念数据同步（akshare → PostgreSQL）
- 股票基础信息同步（TuShare → PostgreSQL）

### 5.2 接口定义

```python
class BasicDataSyncService(SyncServiceBase):
    """基础数据同步服务。"""

    def _get_service_name(self) -> str:
        return "BasicDataSyncService"

    async def run_concept_sync(self) -> ConceptSyncResult:
        """
        执行概念数据同步。

        从 akshare 获取概念数据，同步到 PostgreSQL。

        Returns:
            ConceptSyncResult，包含:
            - total_concepts: 总概念数
            - success_concepts: 成功同步的概念数
            - failed_concepts: 失败的概念数
            - total_stocks: 总成份股数
            - elapsed_time: 耗时（秒）
        """
        ...

    async def run_stock_basic_sync(self) -> dict:
        """
        执行股票基础信息同步。

        从 TuShare 获取股票基础信息，同步到 PostgreSQL。

        Returns:
            同步结果摘要字典，包含:
            - synced_count: 同步成功的记录数
            - message: 状态消息
            - status: 状态（success/failed）
        """
        ...
```

### 5.3 行为规格

#### Scenario: 概念数据同步成功
- **Given** 概念数据源可用
- **When** 调用 `run_concept_sync`
- **Then**
  - 使用 DataEngineeringContainer 创建 SyncConceptDataCmd
  - 执行概念数据同步
  - 返回 ConceptSyncResult
  - success_concepts > 0

#### Scenario: 股票基础信息同步成功
- **Given** TuShare 数据源可用
- **When** 调用 `run_stock_basic_sync`
- **Then**
  - 使用 SyncUseCaseFactory 创建同步用例
  - 执行股票基础信息同步
  - 返回包含 synced_count 和 status 的字典
  - status = "success"

### 5.4 验收标准

- [ ] `BasicDataSyncService` 继承 `SyncServiceBase`
- [ ] `run_concept_sync` 方法迁移成功
- [ ] `run_stock_basic_sync` 方法迁移成功
- [ ] 使用 `_execute_with_tracking` 封装模板代码
- [ ] 单元测试覆盖概念同步和股票基础信息同步场景

---

## 6. 迁移策略

### 阶段 1: 创建新 Service (向后兼容)

```
Week 1
├─ 创建 SyncServiceBase
├─ 创建 DailySyncService (迁移日线方法)
├─ 创建 FinanceSyncService (迁移财务方法)
├─ 更新 DataSyncApplicationService 委托给新 Service
└─ 所有测试通过
```

### 阶段 2: 创建剩余 Service

```
Week 2
├─ 创建 MarketDataSyncService (迁移 AkShare 市场数据方法)
├─ 创建 BasicDataSyncService (迁移基础数据方法)
├─ 更新 DataSyncApplicationService 委托给新 Service
└─ 所有测试通过
```

### 阶段 3: 更新调用方

```
Week 3
├─ 更新 sync_scheduler.py 直接调用新 Service
├─ 更新 akshare_market_data_jobs.py 直接调用 MarketDataSyncService
├─ 更新其他调用方
└─ 所有测试通过
```

### 阶段 4: 移除兼容层 (可选)

```
Week 4
├─ 确认所有调用方已更新
├─ 移除 DataSyncApplicationService
├─ 更新文档
└─ 所有测试通过
```

---

## 7. 接口变更对照表

| 原方法 (DataSyncApplicationService) | 新 Service | 新方法 |
|-----------------------------------|-----------|--------|
| `run_daily_incremental_sync()` | DailySyncService | `run_incremental_sync()` |
| `run_daily_history_sync()` | DailySyncService | `run_history_sync()` |
| `run_incremental_finance_sync()` | FinanceSyncService | `run_incremental_sync()` |
| `run_finance_history_sync()` | FinanceSyncService | `run_history_sync()` |
| `run_akshare_market_data_sync()` | MarketDataSyncService | `run_sync()` |
| `run_concept_sync()` | BasicDataSyncService | `run_concept_sync()` |
| `run_stock_basic_sync()` | BasicDataSyncService | `run_stock_basic_sync()` |

---

## 8. 测试策略

### 单元测试

每个新的 Service 需要单元测试覆盖：

```python
# tests/unit/modules/data_engineering/application/services/test_daily_sync_service.py
class TestDailySyncService:
    async def test_run_incremental_sync_success(self):
        """测试日线增量同步成功。"""
        ...

    async def test_run_history_sync_success(self):
        """测试日线历史同步成功。"""
        ...

    async def test_run_incremental_sync_with_exception(self):
        """测试同步过程中出现异常时的处理。"""
        ...
```

### 集成测试

验证 Service 与 Factory、Container 的集成：

```python
# tests/integration/modules/data_engineering/application/services/test_sync_services.py
class TestSyncServicesIntegration:
    async def test_daily_sync_service_with_factory(self):
        """测试 DailySyncService 与 SyncUseCaseFactory 的集成。"""
        ...
```

### 兼容性测试

验证 `DataSyncApplicationService` 的委托逻辑：

```python
class TestDataSyncApplicationServiceCompatibility:
    async def test_delegates_to_daily_sync_service(self):
        """验证日线同步方法正确委托给 DailySyncService。"""
        ...

    async def test_delegates_to_finance_sync_service(self):
        """验证财务同步方法正确委托给 FinanceSyncService。"""
        ...
```

---

## 9. 文档更新

需要更新的文档：

1. **API 文档**: 更新 Service 接口说明
2. **架构文档**: 更新架构图，展示新的 Service 结构
3. **开发者指南**: 添加关于如何选择使用哪个 Service 的指南
4. **变更日志**: 记录这次重构

---

## 10. 回滚计划

如果重构引入严重问题，回滚策略：

1. **阶段 1-2**: 直接恢复 `DataSyncApplicationService` 的原始实现，新的 Service 类可以保留但不使用
2. **阶段 3**: 恢复 `sync_scheduler.py` 和 `akshare_market_data_jobs.py` 的原始实现
3. **阶段 4**: 如果需要恢复 `DataSyncApplicationService`，可以从 git 历史中提取

所有阶段都通过版本控制管理，可以轻松回滚。
