## 1. 配置外部化

- [x] 1.1 在 `src/shared/config.py` 的 `Settings` 中新增同步相关配置项：`SYNC_DAILY_HISTORY_BATCH_SIZE`（默认 50）、`SYNC_FINANCE_HISTORY_BATCH_SIZE`（默认 100）、`SYNC_FINANCE_HISTORY_START_DATE`（默认 `"20200101"`）、`SYNC_INCREMENTAL_MISSING_LIMIT`（默认 300）、`SYNC_FAILURE_MAX_RETRIES`（默认 3）、`TUSHARE_MIN_INTERVAL`（默认 0.35）
- [x] 1.2 修改 `TushareClient`：将硬编码的 `TUSHARE_MIN_INTERVAL = 0.35` 替换为从 `settings.TUSHARE_MIN_INTERVAL` 读取

## 2. Domain 层——同步状态建模

- [x] 2.1 新增枚举 `SyncJobType`（DAILY_HISTORY / FINANCE_HISTORY / DAILY_INCREMENTAL / FINANCE_INCREMENTAL）和 `SyncTaskStatus`（PENDING / RUNNING / COMPLETED / FAILED / PAUSED），放在 `domain/model/enums.py`
- [x] 2.2 新增 `SyncTask` 实体（`domain/model/sync_task.py`）：包含 `id`、`job_type`、`status`、`current_offset`、`batch_size`、`total_processed`、`started_at`、`updated_at`、`completed_at`、`config`
- [x] 2.3 新增 `SyncFailureRecord` 实体（`domain/model/sync_failure_record.py`）：包含 `id`、`job_type`、`third_code`、`error_message`、`retry_count`、`max_retries`、`last_attempt_at`、`resolved_at`
- [x] 2.4 新增 `ISyncTaskRepository` Port（`domain/ports/repositories/sync_task_repo.py`）：定义 `create`、`update`、`get_latest_by_job_type`（查找最近的 RUNNING/PAUSED 任务）、`create_failure`、`update_failure`、`get_unresolved_failures`（按 job_type 查询未解决且 retry_count < max_retries 的失败）、`resolve_failure` 等抽象方法

## 3. Infrastructure 层——数据库持久化

- [x] 3.1 新增 SQLAlchemy ORM 模型 `SyncTaskModel`（`infrastructure/persistence/models/sync_task_model.py`）：映射到 `sync_tasks` 表
- [x] 3.2 新增 SQLAlchemy ORM 模型 `SyncFailureRecordModel`（`infrastructure/persistence/models/sync_failure_model.py`）：映射到 `sync_failure_records` 表
- [x] 3.3 创建 Alembic migration 脚本：新增 `sync_tasks` 和 `sync_failure_records` 两张表
- [x] 3.4 实现 `SyncTaskRepositoryImpl`（`infrastructure/persistence/repositories/pg_sync_task_repo.py`）：实现 `ISyncTaskRepository` 的所有方法

## 4. Infrastructure 层——限速策略收敛

- [x] 4.1 修改 `TushareClient._rate_limited_call()`：从 `settings.TUSHARE_MIN_INTERVAL` 读取限速参数（替代模块级常量）
- [x] 4.2 移除 `SyncDailyHistoryUseCase` 中的 `asyncio.Semaphore(5)` 和 `asyncio.sleep(0.1)` 限速代码，改为纯串行调用（限速完全由 TushareClient 负责）

## 5. Application 层——SyncEngine 同步引擎

- [x] 5.1 新增 `SyncEngine` 应用服务（`application/commands/sync_engine.py`）：构造函数接收 `ISyncTaskRepository`、`IStockBasicRepository`、`IMarketQuoteRepository`、`IFinancialDataRepository`、`IMarketQuoteProvider`、`IFinancialDataProvider`
- [x] 5.2 实现 `SyncEngine.run_history_sync(job_type, config)`：查找或恢复 SyncTask → 循环分批调用对应 Use Case → 每批更新进度 → batch 返回 0 时标记 COMPLETED → 异常时记录 SyncFailureRecord
- [x] 5.3 实现同类型任务互斥：`run_history_sync` 启动前检查是否存在 RUNNING 状态的同类型 SyncTask，存在则拒绝并返回已有任务
- [x] 5.4 实现断点续跑：`run_history_sync` 启动时查找最近的 RUNNING/PAUSED 同类型 SyncTask，存在则从其 `current_offset` 恢复

## 6. Application 层——增量同步增强

- [x] 6.1 重构 `SyncDailyByDateUseCase`（或新增增量日线方法到 SyncEngine）：执行前查询 `max(trade_date)`，与 today 比较，若有间隔则按缺失日期区间逐日补同步；无遗漏则仅同步 today；DB 为空时记录警告并仅同步 today
- [x] 6.2 重构 `SyncIncrementalFinanceDataUseCase`：移除 `_save_failures` 方法和 `FAILURE_RECORD_FILE` 常量；失败记录改为通过 `ISyncTaskRepository.create_failure` 写入 DB
- [x] 6.3 在增量财务同步执行前增加失败重试步骤：查询 `get_unresolved_failures(job_type=FINANCE_INCREMENTAL)` → 逐条重试 → 成功则 `resolve_failure`，失败则递增 `retry_count`
- [x] 6.4 将 `SyncIncrementalFinanceDataUseCase` 中硬编码的 `limit=300` 替换为从 `settings.SYNC_INCREMENTAL_MISSING_LIMIT` 读取

## 7. Application 层——DI 工厂

- [x] 7.1 新增 `SyncUseCaseFactory`（`application/factories/sync_factory.py`）：提供 `create_sync_engine()` 异步上下文管理器，封装 session 创建、repo/provider 实例化和 SyncEngine 装配
- [x] 7.2 工厂需支持每批独立 session：提供 `create_batch_session()` 方法（或在 SyncEngine 内部按批创建 session），确保长任务不长期持有单一连接

## 8. Presentation 层——重写 sync_scheduler

- [x] 8.1 重写 `sync_scheduler.py`：移除所有 Infrastructure 层的直接 import（`StockRepositoryImpl`、`StockDailyRepositoryImpl`、`StockFinanceRepositoryImpl`、`TushareClient`）
- [x] 8.2 移除所有 JSON 文件状态函数（`load_offset`、`save_offset`、`load_finance_offset`、`save_finance_offset`、`load_finance_failures`、`save_finance_failures`、`append_finance_failures`）及相关常量（`STATE_FILE`、`FINANCE_STATE_FILE`、`FINANCE_FAILURE_FILE`）
- [x] 8.3 重写 `sync_history_daily_data_job`：通过 `SyncUseCaseFactory.create_sync_engine()` 获取 SyncEngine，调用 `run_history_sync(DAILY_HISTORY, config)`
- [x] 8.4 重写 `sync_daily_data_job`：通过工厂获取 SyncEngine，调用增量日线同步（含补偿逻辑）
- [x] 8.5 重写 `sync_finance_history_job`：通过工厂获取 SyncEngine，调用 `run_history_sync(FINANCE_HISTORY, config)`，`start_date`/`end_date` 从配置读取
- [x] 8.6 重写 `sync_incremental_finance_job`：通过工厂获取 SyncEngine，调用增量财务同步（含失败重试）
- [x] 8.7 更新 `scheduler_routes.py` 的 `JOB_REGISTRY`，确保路由映射指向重写后的 job 函数（REST API 路径和响应格式保持不变）

## 9. 测试

- [x] 9.1 单元测试：`SyncTask` 和 `SyncFailureRecord` 实体创建与状态转换
- [x] 9.2 单元测试：`SyncEngine.run_history_sync` ——mock Use Case 和 ISyncTaskRepository，验证分批循环、进度更新、COMPLETED 标记
- [x] 9.3 单元测试：`SyncEngine` 同类型互斥——已有 RUNNING 任务时拒绝启动
- [x] 9.4 单元测试：`SyncEngine` 断点续跑——存在 RUNNING/PAUSED 任务时从 `current_offset` 恢复
- [x] 9.5 单元测试：增量日线补偿——mock `max(trade_date)` 返回不同日期，验证补偿行为（无遗漏/有遗漏/DB 为空）
- [x] 9.6 单元测试：增量财务失败重试——验证先重试未解决记录 → 成功标记 resolved → 失败递增 retry_count → 超限不重试
- [x] 9.7 单元测试：配置外部化——验证 Settings 中新增配置项的默认值和环境变量覆盖
- [x] 9.8 集成测试：`SyncTaskRepositoryImpl` CRUD 操作——创建、更新、按 job_type 查询、失败记录读写
- [x] 9.9 代码审查验证：`sync_scheduler.py` 无 Infrastructure 直接 import；Use Case 无 Semaphore/sleep 限速代码；无 JSON 文件依赖
