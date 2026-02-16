# Proposal: 拆分 DataSyncApplicationService

## 背景与问题

`DataSyncApplicationService` 当前负责 8 种不同的数据同步任务：

1. **日线数据同步** (2个方法): `run_daily_incremental_sync`, `run_daily_history_sync`
2. **财务数据同步** (2个方法): `run_incremental_finance_sync`, `run_finance_history_sync`
3. **基础数据同步** (4个方法): `run_concept_sync`, `run_stock_basic_sync`, `run_akshare_market_data_sync`

**代码统计**:
- 文件行数: ~255 行
- 方法数量: 8 个
- 代码重复: 每个方法都重复相同的 "session + ExecutionTracker" 模板代码

**架构问题**:
1. **违反单一职责原则 (SRP)**: 一个类同时负责日线、财务、基础数据三大类完全不同的同步逻辑
2. **测试困难**: 测试财务同步逻辑时，被迫加载所有其他同步的依赖
3. **变更风险**: 修改财务同步代码时，可能意外影响日线同步功能
4. **代码膨胀**: 随着新数据类型增加，这个类会继续膨胀

## 目标

将 `DataSyncApplicationService` 按数据类型拆分为 4 个专门的 Service：

```
DataSyncApplicationService
    ├── DailySyncService          # 日线数据同步
    ├── FinanceSyncService        # 财务数据同步
    ├── MarketDataSyncService     # AkShare 市场数据同步
    └── BasicDataSyncService      # 基础数据同步（概念、股票基础信息）
```

同时提取公共模板到 `SyncServiceBase`，消除重复代码。

## 范围

**包含**:
1. 创建 4 个新的 Service 类，从原 Service 迁移对应方法
2. 创建 `SyncServiceBase` 基类，封装公共模板（session、ExecutionTracker）
3. 更新 `DataSyncApplicationService`，使其方法委托给新的专门 Service
4. 更新 `sync_scheduler.py` 和 `akshare_market_data_jobs.py` 中对新 Service 的调用
5. 确保所有现有测试仍然通过

**不包含**:
- 修改任何同步业务逻辑本身
- 新增或删除同步任务类型
- 修改 Repository、Provider 等底层实现
- 修改 REST API 接口

## 影响

**正向影响**:
- 代码更清晰，每个 Service 职责单一
- 更容易测试，每个 Service 可以独立单元测试
- 更容易维护，修改一个数据类型的同步不会影响其他
- 更容易扩展，新增数据类型只需创建新的 Service

**风险与缓解**:
- **风险**: 拆分过程中可能引入回归 bug
  - **缓解**: 保持所有现有测试通过，逐步迁移，不修改业务逻辑
- **风险**: 调用方需要更新引用
  - **缓解**: 先在 `DataSyncApplicationService` 中委托给新 Service，保持对外接口不变，逐步迁移调用方

## 验收标准

- [ ] `DailySyncService` 创建并包含日线相关同步方法
- [ ] `FinanceSyncService` 创建并包含财务相关同步方法
- [ ] `MarketDataSyncService` 创建并包含 AkShare 市场数据同步方法
- [ ] `BasicDataSyncService` 创建并包含基础数据同步方法
- [ ] `SyncServiceBase` 创建，封装公共模板代码
- [ ] 所有现有测试通过
- [ ] 代码覆盖率不下降

## 下一步

1. 设计详细方案：确定每个 Service 的接口和方法签名
2. 创建任务列表：按 Service 逐个迁移
3. 开始实施：从 `SyncServiceBase` 开始，然后逐个迁移
