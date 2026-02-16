# Tasks: DataSyncApplicationService 拆分

## 任务总览

| 阶段 | 任务数 | 预计工期 |
|------|--------|----------|
| 1. 基础设施 | 2 | 2 天 |
| 2. DailySyncService | 2 | 2 天 |
| 3. FinanceSyncService | 2 | 2 天 |
| 4. MarketDataSyncService | 2 | 2 天 |
| 5. BasicDataSyncService | 2 | 2 天 |
| 6. 兼容层与更新 | 3 | 3 天 |
| 7. 测试与验收 | 2 | 2 天 |
| **总计** | **17** | **~17 天** |

---

## 阶段 1: 基础设施

### Task 1.1: 创建 SyncServiceBase 基类

**优先级**: P0 (阻塞后续所有任务)
**依赖**: 无

**描述**:
创建 `SyncServiceBase` 抽象基类，封装所有数据同步服务共有的模板代码。

**工作内容**:
1. 创建目录 `src/modules/data_engineering/application/services/base/`
2. 创建 `__init__.py` 导出 `SyncServiceBase`
3. 创建 `sync_service_base.py` 实现基类:
   - `__init__` 方法绑定日志记录器
   - `_get_service_name` 抽象方法
   - `_execute_with_tracking` 模板方法

**验收标准**:
- [ ] `SyncServiceBase` 抽象类可以正确导入
- [ ] 子类必须实现 `_get_service_name` 方法
- [ ] `_execute_with_tracking` 正确封装 session 和 ExecutionTracker
- [ ] 日志记录包含服务名称

**测试要求**:
- [ ] 🔴 编写测试: 子类未实现抽象方法时应抛出 TypeError
- [ ] 🔴 编写测试: `_execute_with_tracking` 正常执行流程
- [ ] 🔴 编写测试: `_execute_with_tracking` 异常传播

---

### Task 1.2: 创建测试基础设施

**优先级**: P0
**依赖**: Task 1.1

**描述**:
为新 Service 创建测试目录结构和公共 fixtures。

**工作内容**:
1. 创建 `tests/unit/modules/data_engineering/application/services/` 目录
2. 创建 `conftest.py` 定义 Service 测试的公共 fixtures:
   - `mock_session`: 模拟 AsyncSession
   - `mock_execution_tracker`: 模拟 ExecutionTracker
   - `mock_sync_engine`: 模拟 SyncEngine
   - `mock_use_case_factory`: 模拟 SyncUseCaseFactory

**验收标准**:
- [ ] 测试目录结构符合项目规范
- [ ] conftest.py 可以被 pytest 自动加载
- [ ] fixtures 可以在测试函数中正常使用

**测试要求**:
- [ ] 验证 fixtures 可以正确 mock 依赖

---

## 阶段 2: DailySyncService

### Task 2.1: 创建 DailySyncService

**优先级**: P1
**依赖**: Task 1.1, Task 1.2

**描述**:
创建 `DailySyncService`，从 `DataSyncApplicationService` 迁移日线相关方法。

**工作内容**:
1. 创建 `daily_sync_service.py`:
   - 继承 `SyncServiceBase`
   - 实现 `_get_service_name` 返回 "DailySyncService"
   - 实现 `run_incremental_sync` 方法
   - 实现 `run_history_sync` 方法
2. 两个方法都使用 `_execute_with_tracking` 封装模板代码

**验收标准**:
- [ ] `DailySyncService` 可以正确导入
- [ ] 两个方法都使用 `_execute_with_tracking`
- [ ] 日志记录包含 "DailySyncService" 前缀
- [ ] 方法签名和返回值与原实现一致

**测试要求**:
- [ ] 🔴 编写测试: `run_incremental_sync` 成功场景
- [ ] 🔴 编写测试: `run_history_sync` 成功场景
- [ ] 🔴 编写测试: 异常情况处理

---

### Task 2.2: 迁移日线方法并验证

**优先级**: P1
**依赖**: Task 2.1

**描述**:
更新 `DataSyncApplicationService`，将日线方法委托给 `DailySyncService`。

**工作内容**:
1. 在 `DataSyncApplicationService.__init__` 中创建 `DailySyncService` 实例
2. 修改 `run_daily_incremental_sync` 方法，委托给 `DailySyncService.run_incremental_sync`
3. 修改 `run_daily_history_sync` 方法，委托给 `DailySyncService.run_history_sync`

**验收标准**:
- [ ] `DataSyncApplicationService` 仍然可以正常导入和使用
- [ ] 日线同步方法通过委托调用 `DailySyncService`
- [ ] 所有现有测试仍然通过

**测试要求**:
- [ ] 运行现有测试套件，确保无回归

---

## 阶段 3: FinanceSyncService

### Task 3.1: 创建 FinanceSyncService

**优先级**: P1
**依赖**: Task 1.1

**描述**:
创建 `FinanceSyncService`，从 `DataSyncApplicationService` 迁移财务相关方法。

**工作内容**:
1. 创建 `finance_sync_service.py`:
   - 继承 `SyncServiceBase`
   - 实现 `_get_service_name` 返回 "FinanceSyncService"
   - 实现 `run_incremental_sync` 方法
   - 实现 `run_history_sync` 方法

**验收标准**:
- [ ] `FinanceSyncService` 可以正确导入
- [ ] 两个方法都使用 `_execute_with_tracking`
- [ ] 日志记录包含 "FinanceSyncService" 前缀
- [ ] 方法签名和返回值与原实现一致

**测试要求**:
- [ ] 🔴 编写测试: `run_incremental_sync` 成功场景
- [ ] 🔴 编写测试: `run_history_sync` 成功场景
- [ ] 🔴 编写测试: 异常情况处理

---

### Task 3.2: 迁移财务方法并验证

**优先级**: P1
**依赖**: Task 3.1

**描述**:
更新 `DataSyncApplicationService`，将财务方法委托给 `FinanceSyncService`。

**工作内容**:
1. 在 `DataSyncApplicationService.__init__` 中创建 `FinanceSyncService` 实例
2. 修改 `run_incremental_finance_sync` 方法，委托给 `FinanceSyncService.run_incremental_sync`
3. 修改 `run_finance_history_sync` 方法，委托给 `FinanceSyncService.run_history_sync`

**验收标准**:
- [ ] `DataSyncApplicationService` 仍然可以正常导入和使用
- [ ] 财务同步方法通过委托调用 `FinanceSyncService`
- [ ] 所有现有测试仍然通过

**测试要求**:
- [ ] 运行现有测试套件，确保无回归

---

## 阶段 4: MarketDataSyncService

### Task 4.1: 创建 MarketDataSyncService

**优先级**: P1
**依赖**: Task 1.1

**描述**:
创建 `MarketDataSyncService`，从 `DataSyncApplicationService` 迁移 AkShare 市场数据同步方法。

**工作内容**:
1. 创建 `market_data_sync_service.py`:
   - 继承 `SyncServiceBase`
   - 实现 `_get_service_name` 返回 "MarketDataSyncService"
   - 实现 `run_sync` 方法

**验收标准**:
- [ ] `MarketDataSyncService` 可以正确导入
- [ ] `run_sync` 方法使用 `_execute_with_tracking`
- [ ] 日志记录包含 "MarketDataSyncService" 前缀
- [ ] 方法签名和返回值与原实现一致

**测试要求**:
- [ ] 🔴 编写测试: `run_sync` 全部成功场景
- [ ] 🔴 编写测试: `run_sync` 部分失败场景
- [ ] 🔴 编写测试: 异常情况处理

---

### Task 4.2: 迁移市场数据方法并验证

**优先级**: P1
**依赖**: Task 4.1

**描述**:
更新 `DataSyncApplicationService`，将市场数据方法委托给 `MarketDataSyncService`；同时更新 `akshare_market_data_jobs.py`。

**工作内容**:
1. 在 `DataSyncApplicationService.__init__` 中创建 `MarketDataSyncService` 实例
2. 修改 `run_akshare_market_data_sync` 方法，委托给 `MarketDataSyncService.run_sync`
3. 更新 `akshare_market_data_jobs.py`，直接导入和调用 `MarketDataSyncService`

**验收标准**:
- [ ] `DataSyncApplicationService` 仍然可以正常导入和使用
- [ ] 市场数据同步方法通过委托调用 `MarketDataSyncService`
- [ ] `akshare_market_data_jobs.py` 直接调用 `MarketDataSyncService`
- [ ] 所有现有测试仍然通过

**测试要求**:
- [ ] 运行现有测试套件，确保无回归

---

## 阶段 5: BasicDataSyncService

### Task 5.1: 创建 BasicDataSyncService

**优先级**: P1
**依赖**: Task 1.1

**描述**:
创建 `BasicDataSyncService`，从 `DataSyncApplicationService` 迁移基础数据同步方法。

**工作内容**:
1. 创建 `basic_data_sync_service.py`:
   - 继承 `SyncServiceBase`
   - 实现 `_get_service_name` 返回 "BasicDataSyncService"
   - 实现 `run_concept_sync` 方法
   - 实现 `run_stock_basic_sync` 方法

**验收标准**:
- [ ] `BasicDataSyncService` 可以正确导入
- [ ] 两个方法都使用 `_execute_with_tracking`
- [ ] 日志记录包含 "BasicDataSyncService" 前缀
- [ ] 方法签名和返回值与原实现一致

**测试要求**:
- [ ] 🔴 编写测试: `run_concept_sync` 成功场景
- [ ] 🔴 编写测试: `run_stock_basic_sync` 成功场景
- [ ] 🔴 编写测试: 异常情况处理

---

### Task 5.2: 迁移基础数据方法并验证

**优先级**: P1
**依赖**: Task 5.1

**描述**:
更新 `DataSyncApplicationService`，将基础数据方法委托给 `BasicDataSyncService`。

**工作内容**:
1. 在 `DataSyncApplicationService.__init__` 中创建 `BasicDataSyncService` 实例
2. 修改 `run_concept_sync` 方法，委托给 `BasicDataSyncService.run_concept_sync`
3. 修改 `run_stock_basic_sync` 方法，委托给 `BasicDataSyncService.run_stock_basic_sync`

**验收标准**:
- [ ] `DataSyncApplicationService` 仍然可以正常导入和使用
- [ ] 基础数据同步方法通过委托调用 `BasicDataSyncService`
- [ ] 所有现有测试仍然通过

**测试要求**:
- [ ] 运行现有测试套件，确保无回归

---

## 阶段 6: 兼容层与调用方更新

### Task 6.1: 更新 sync_scheduler.py

**优先级**: P1
**依赖**: Task 2.2, Task 3.2, Task 5.2

**描述**:
更新 `sync_scheduler.py`，直接导入和调用新的专门 Service。

**工作内容**:
1. 更新导入语句，从新的 Service 文件导入
2. 每个 Job 函数直接创建对应的 Service 实例并调用
3. 移除对 `DataSyncApplicationService` 的依赖

**代码变更示例**:

```python
# Before
from src.modules.data_engineering.application.services.data_sync_application_service import (
    DataSyncApplicationService,
)

async def sync_daily_data_job(target_date: str | None = None):
    service = DataSyncApplicationService()
    await service.run_daily_incremental_sync(target_date)

# After
from src.modules.data_engineering.application.services.daily_sync_service import (
    DailySyncService,
)

async def sync_daily_data_job(target_date: str | None = None):
    service = DailySyncService()
    await service.run_incremental_sync(target_date)
```

**验收标准**:
- [ ] `sync_scheduler.py` 成功更新
- [ ] 每个 Job 函数直接调用对应的专门 Service
- [ ] 所有现有测试仍然通过

**测试要求**:
- [ ] 运行现有测试套件，确保无回归
- [ ] 手动验证定时任务可以正常调度

---

### Task 6.2: 更新 akshare_market_data_jobs.py

**优先级**: P1
**依赖**: Task 4.2

**描述**:
更新 `akshare_market_data_jobs.py`，直接导入和调用 `MarketDataSyncService`。

**工作内容**:
1. 更新导入语句，从 `market_data_sync_service` 导入
2. Job 函数直接创建 `MarketDataSyncService` 实例并调用
3. 移除对 `DataSyncApplicationService` 的依赖

**验收标准**:
- [ ] `akshare_market_data_jobs.py` 成功更新
- [ ] Job 函数直接调用 `MarketDataSyncService`
- [ ] 所有现有测试仍然通过

**测试要求**:
- [ ] 运行现有测试套件，确保无回归

---

### Task 6.3: 标记 DataSyncApplicationService 为弃用

**优先级**: P2
**依赖**: Task 6.1, Task 6.2

**描述**:
添加弃用警告到 `DataSyncApplicationService`，引导调用方迁移到新的专门 Service。

**工作内容**:
1. 在 `DataSyncApplicationService.__init__` 中添加弃用警告
2. 更新类文档字符串，说明已弃用并指向新的 Service
3. 在每个方法文档字符串中添加弃用说明

**代码示例**:

```python
import warnings

class DataSyncApplicationService:
    """
    数据同步应用服务（已弃用）。

    ⚠️ 已弃用: 此类已拆分为专门的 Service:
    - DailySyncService: 日线数据同步
    - FinanceSyncService: 财务数据同步
    - MarketDataSyncService: AkShare 市场数据同步
    - BasicDataSyncService: 基础数据同步

    此类现在仅作为兼容层，方法委托给上述专门 Service。
    请直接调用专门的 Service。
    """

    def __init__(self):
        warnings.warn(
            "DataSyncApplicationService is deprecated. "
            "Use DailySyncService, FinanceSyncService, MarketDataSyncService, "
            "or BasicDataSyncService directly.",
            DeprecationWarning,
            stacklevel=2,
        )
        self._daily_service = DailySyncService()
        # ... 其他 Service
```

**验收标准**:
- [ ] `DataSyncApplicationService` 使用时发出弃用警告
- [ ] 文档字符串说明已弃用并指向新的 Service
- [ ] 弃用信息清晰，包含迁移指南

**测试要求**:
- [ ] 验证弃用警告被正确触发

---

## 阶段 7: 测试与验收

### Task 7.1: 全面测试

**优先级**: P0
**依赖**: 所有实施任务

**描述**:
运行全面的测试套件，确保重构没有引入回归。

**工作内容**:
1. 运行单元测试: `pytest tests/unit/`
2. 运行集成测试: `pytest tests/integration/`
3. 运行 E2E 测试: `pytest tests/e2e/`
4. 检查代码覆盖率: `pytest --cov`
5. 手动验证关键流程

**验收标准**:
- [ ] 所有单元测试通过
- [ ] 所有集成测试通过
- [ ] 所有 E2E 测试通过
- [ ] 代码覆盖率不下降（或提升）
- [ ] 手动验证通过

**测试要求**:
- [ ] 全面测试报告

---

### Task 7.2: 代码审查与文档更新

**优先级**: P1
**依赖**: Task 7.1

**描述**:
进行代码审查，更新相关文档。

**工作内容**:
1. 代码审查:
   - 检查代码风格和规范
   - 检查类型提示
   - 检查文档字符串
   - 检查错误处理
2. 文档更新:
   - 更新架构文档
   - 更新 API 文档
   - 更新开发者指南
   - 更新变更日志

**验收标准**:
- [ ] 代码审查完成，问题已修复
- [ ] 架构文档更新
- [ ] API 文档更新
- [ ] 开发者指南更新
- [ ] 变更日志更新

**测试要求**:
- [ ] 文档审阅和确认

---

## 任务依赖图

```
Task 1.1: 创建 SyncServiceBase 基类
    │
    ├──► Task 1.2: 创建测试基础设施
    │
    ├──► Task 2.1: 创建 DailySyncService
    │       └──► Task 2.2: 迁移日线方法
    │
    ├──► Task 3.1: 创建 FinanceSyncService
    │       └──► Task 3.2: 迁移财务方法
    │
    ├──► Task 4.1: 创建 MarketDataSyncService
    │       └──► Task 4.2: 迁移市场数据方法
    │               └──► Task 6.2: 更新 akshare_market_data_jobs.py
    │
    └──► Task 5.1: 创建 BasicDataSyncService
            └──► Task 5.2: 迁移基础数据方法

Task 2.2 + Task 3.2 + Task 5.2
    └──► Task 6.1: 更新 sync_scheduler.py

Task 6.1 + Task 6.2
    └──► Task 6.3: 标记 DataSyncApplicationService 为弃用

Task 6.3
    └──► Task 7.1: 全面测试

Task 7.1
    └──► Task 7.2: 代码审查与文档更新
```

---

## 执行建议

### 建议的迭代节奏

**迭代 1 (Week 1)**: 基础设施 + DailySyncService
- Task 1.1, 1.2, 2.1, 2.2

**迭代 2 (Week 2)**: FinanceSyncService + MarketDataSyncService
- Task 3.1, 3.2, 4.1, 4.2

**迭代 3 (Week 3)**: BasicDataSyncService + 兼容层
- Task 5.1, 5.2, 6.1, 6.2, 6.3

**迭代 4 (Week 4)**: 测试与文档
- Task 7.1, 7.2

### 风险缓解

- **并行开发**: Task 2.1、3.1、4.1、5.1 可以并行开发，但需要等待 Task 1.1 完成
- **早期验证**: 每个 Service 完成后立即进行集成测试，不要等所有 Service 完成
- **快速反馈**: 建议每个迭代结束时运行完整测试套件

### 检查点

- [ ] **检查点 1** (迭代 1 结束): DailySyncService 完成，所有测试通过
- [ ] **检查点 2** (迭代 2 结束): FinanceSyncService 和 MarketDataSyncService 完成，所有测试通过
- [ ] **检查点 3** (迭代 3 结束): 所有 Service 完成，sync_scheduler.py 更新，所有测试通过
- [ ] **检查点 4** (迭代 4 结束): 文档更新，代码审查完成，准备合并
