# Spec: foundation-scheduler-service

Foundation 模块的调度器服务能力——完整的 DDD 四层结构、SchedulerPort 接口契约、Application Service 编排、Job 注册机制、REST API、DI 集成以及领域异常体系。

**测试约定**：每个 `#### Scenario:` 在变更**交付时**须对应至少一个自动化测试用例（单元或集成）；实现顺序可先实现再补测，以完整测试通过为需求完成标准。

---

## ADDED Requirements

### Requirement: Foundation 模块目录结构

系统 SHALL 在 `src/modules/foundation/` 下建立标准 DDD 四层目录结构。顶层目录 SHALL 包含 `application/`、`domain/`、`infrastructure/`、`presentation/` 四个子包，每个子包 SHALL 包含 `__init__.py`。模块 SHALL 在 `vision-and-modules.md` 的模块注册表（§4.2 支撑与通用模块）中注册。

#### Scenario: 模块目录完整性

- **WHEN** 审查 `src/modules/foundation/` 目录结构
- **THEN** SHALL 存在以下子包：`application/services/`、`application/dtos/`、`domain/ports/`、`domain/dtos/`、`infrastructure/adapters/`、`infrastructure/persistence/`、`infrastructure/di/`、`presentation/rest/`，且每个目录包含 `__init__.py`

#### Scenario: 模块注册表更新

- **WHEN** 审查 `vision-and-modules.md` 的模块注册表
- **THEN** SHALL 存在 Foundation 模块条目，路径为 `src/modules/foundation/`，核心职责为公共支撑能力（调度、消息推送等横切关注点）

---

### Requirement: SchedulerPort 完整接口契约

系统 SHALL 在 `src/modules/foundation/domain/ports/scheduler_port.py` 中定义 `SchedulerPort` 抽象基类（ABC）。`SchedulerPort` SHALL 包含以下抽象方法：

- `schedule_job(job_id, job_func, cron_expression, timezone, **kwargs)`: 调度定时任务
- `start_scheduler()`: 启动调度器
- `shutdown_scheduler()`: 关闭调度器
- `get_job_status(job_id)`: 获取任务状态
- `get_all_jobs()`: 获取所有任务信息
- `remove_job(job_id)`: 移除已调度的任务
- `trigger_job(job_id, **kwargs)`: 立即触发一次任务执行

#### Scenario: 接口方法完整性

- **WHEN** 审查 `SchedulerPort` 抽象方法
- **THEN** SHALL 包含上述 7 个抽象方法，每个方法都有正确的类型注解

#### Scenario: 接口不可实例化

- **WHEN** 尝试直接实例化 `SchedulerPort`
- **THEN** SHALL 抛出 `TypeError` 异常

#### Scenario: remove_job 和 trigger_job 直接调用

- **WHEN** 检查 `SchedulerPort` 的 `remove_job` 和 `trigger_job` 方法
- **THEN** SHALL 不需要 `hasattr()` 检查，可直接调用

---

### Requirement: SchedulerApplicationService 编排能力

系统 SHALL 在 `src/modules/foundation/application/services/scheduler_application_service.py` 中提供 `SchedulerApplicationService` 应用服务。该服务 SHALL 通过 DI 注入 `SchedulerPort` 和相关 Repository，提供高级编排操作：

- `schedule_and_persist_job()`: 调度 + 持久化原子编排
- `stop_and_disable_job()`: 移除任务 + 更新 DB enabled=False
- `trigger_job()`: 通过 `SchedulerPort.trigger_job()` 实际触发任务
- `query_execution_logs()`: 通过 DI 注入的 Repository 查询执行历史

#### Scenario: 原子编排调度和持久化

- **WHEN** 调用 `schedule_and_persist_job()` 调度新任务
- **THEN** SHALL 先通过 Repository upsert 配置，成功后再通过 SchedulerPort 调度；任一步骤失败 SHALL 回滚或抛出异常

#### Scenario: 停止任务并禁用配置

- **WHEN** 调用 `stop_and_disable_job()` 停止任务
- **THEN** SHALL 先通过 SchedulerPort 移除任务，成功后更新 DB enabled=False

#### Scenario: 实际触发任务执行

- **WHEN** 调用 `trigger_job()` 触发任务
- **THEN** SHALL 直接委托给 `SchedulerPort.trigger_job()`，不返回伪响应

#### Scenario: 查询执行历史

- **WHEN** 调用 `query_execution_logs()` 查询历史
- **THEN** SHALL 通过 DI 注入的 Repository 查询，返回格式化的执行记录列表

---

### Requirement: Foundation 领域异常体系

系统 SHALL 在 `src/modules/foundation/domain/exceptions.py` 中创建 Scheduler 异常体系。所有异常 SHALL 继承自 `AppException`，包含以下异常类：

- `SchedulerException`: 基础调度异常
- `SchedulerJobNotFoundException`: 任务未找到异常
- `SchedulerJobAlreadyExistsException`: 任务已存在异常
- `SchedulerExecutionException`: 调度执行异常
- `SchedulerConfigurationException`: 调度配置异常

#### Scenario: 异常继承关系

- **WHEN** 检查 Scheduler 异常类
- **THEN** 所有异常 SHALL 继承自 `AppException`

#### Scenario: 异常类存在性

- **WHEN** 审查异常定义
- **THEN** SHALL 存在上述 5 个异常类，每个都有适当的构造函数

---

### Requirement: APScheduler 适配器实现

系统 SHALL 在 `src/modules/foundation/infrastructure/adapters/apscheduler_adapter.py` 中提供 `APSchedulerAdapter` 实现。该适配器 SHALL：

- 实现 `SchedulerPort` 接口的所有抽象方法
- 封装 APScheduler 的具体操作细节
- 使用 AsyncIOScheduler 作为底层调度器
- 正确处理任务不存在、已存在等异常情况

#### Scenario: 适配器接口实现

- **WHEN** 检查 `APSchedulerAdapter` 类
- **THEN** SHALL 继承自 `SchedulerPort` 并实现所有抽象方法

#### Scenario: Cron 表达式解析

- **WHEN** 调度任务时传入无效的 Cron 表达式
- **THEN** SHALL 抛出 `SchedulerExecutionException`

#### Scenario: 任务重复调度检测

- **WHEN** 尝试调度已存在的 job_id
- **THEN** SHALL 抛出 `SchedulerJobAlreadyExistsException`

#### Scenario: 不存在任务操作

- **WHEN** 尝试移除或触发不存在的 job_id
- **THEN** SHALL 抛出 `SchedulerJobNotFoundException`

---

### Requirement: Foundation DI 容器

系统 SHALL 在 `src/modules/foundation/infrastructure/di/container.py` 中创建 Foundation 模块的 DI 容器。该容器 SHALL：

- 注册 `APSchedulerAdapter` 为 Singleton
- 绑定 `SchedulerPort` 到 `APSchedulerAdapter`
- 提供 Repository Factory 函数
- 提供 `SchedulerApplicationService` Factory 函数
- 导出 `get_scheduler_service()` 工厂函数供其他模块使用

#### Scenario: 适配器 Singleton 注册

- **WHEN** 多次调用 DI 容器获取 `APSchedulerAdapter`
- **THEN** SHALL 返回同一个实例

#### Scenario: Port 接口绑定

- **WHEN** 通过 DI 容器请求 `SchedulerPort`
- **THEN** SHALL 返回 `APSchedulerAdapter` 实例

#### Scenario: Service Factory 可用

- **WHEN** 调用 `get_scheduler_service()` 工厂函数
- **THEN** SHALL 返回配置完整的 `SchedulerApplicationService` 实例

---

### Requirement: REST API 端点迁移

系统 SHALL 将调度器相关的 REST API 从 `data_engineering` 模块迁移到 `foundation` 模块。API SHALL 位于 `src/modules/foundation/presentation/rest/scheduler_routes.py`，包含以下端点：

- `POST /jobs/schedule`: 调度任务（委托给 `schedule_and_persist_job()`）
- `POST /jobs/{job_id}/stop`: 停止任务（委托给 `stop_and_disable_job()`）
- `POST /jobs/{job_id}/trigger`: 触发任务（委托给 `trigger_job()`）
- `GET /jobs/{job_id}/executions`: 获取执行历史（委托给 `query_execution_logs()`）
- `GET /jobs`: 获取所有任务状态
- `GET /status`: 获取调度器状态

#### Scenario: 端点委托应用服务

- **WHEN** 调用任何调度器 API 端点
- **THEN** SHALL 委托给 `SchedulerApplicationService` 的相应方法，不直接操作 Repository 或 SchedulerPort

#### Scenario: 路由注册更新

- **WHEN** 审查主路由注册文件
- **THEN** SHALL 从 Foundation 模块导入 scheduler router，而非从 data_engineering

#### Scenario: Schema 迁移

- **WHEN** 检查 API Schema 定义
- **THEN** SHALL 位于 `src/modules/foundation/presentation/rest/scheduler_schemas.py`，包含 `JobDetail`、`SchedulerStatusResponse`、`ExecutionLogDetail`

---

### Requirement: Job 注册机制重构

系统 SHALL 重构 Job 注册机制，避免 Foundation 模块依赖业务模块。系统 SHALL：

- 在 `src/modules/data_engineering/application/job_registry.py` 中创建业务模块的 Job 注册表
- 在 `main.py` 中从各业务模块收集 Job 注册表并合并
- 将合并后的注册表传递给 Foundation 的 `load_persisted_jobs()` 方法
- Foundation 模块不直接 import 业务模块

#### Scenario: 业务模块 Job 注册表

- **WHEN** 审查 `data_engineering/application/job_registry.py`
- **THEN** SHALL 导出 `get_job_registry()` 函数，返回 `Dict[str, Callable]` 映射

#### Scenario: 主模块合并注册表

- **WHEN** 审查 `main.py` 的启动逻辑
- **THEN** SHALL 从 Foundation 导入 `get_scheduler_service`，从各业务模块导入并合并 Job 注册表

#### Scenario: Foundation 无业务依赖

- **WHEN** 检查 Foundation 模块 import 语句
- **THEN** SHALL 不包含任何业务模块的直接 import

---

### Requirement: 共享模块清理

系统 SHALL 清理 `src/shared/` 中已迁移的 Scheduler 相关代码：

- 删除 `domain/ports/scheduler_port.py`
- 删除 `domain/ports/scheduler_job_config_repository_port.py`
- 删除 `domain/dtos/scheduler_dtos.py`
- 删除 `domain/types.py`
- 删除 `application/services/scheduler_service.py`
- 删除 `application/dtos/scheduler_dtos.py`
- 删除 `infrastructure/adapters/apscheduler_adapter.py`
- 删除 `infrastructure/scheduler/` 整个目录
- 清理 `infrastructure/di/` 中的 Scheduler 相关配置

#### Scenario: 共享目录无残留文件

- **WHEN** 搜索 `src/shared/` 中的 scheduler 相关文件
- **THEN** SHALL 不存在任何 Scheduler 相关的 Python 文件

#### Scenario: 全局 Import 路径更新

- **WHEN** 全局搜索旧路径 import
- **THEN** SHALL 不存在 `from src.shared.domain.ports.scheduler_port` 等旧路径 import

#### Scenario: 共享 DI 容器清理

- **WHEN** 审查 `src/shared/infrastructure/di/container.py`
- **THEN** SHALL 不包含任何 Scheduler 相关的 provider 配置
