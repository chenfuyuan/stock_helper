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

| 方法 | 签名 | 职责 |
|------|------|------|
| `schedule_job` | `(job_id: str, job_func: Callable, cron_expression: str, timezone: str, **kwargs) -> None` | 调度 cron 任务 |
| `start_scheduler` | `() -> None` | 启动调度器后台循环 |
| `shutdown_scheduler` | `() -> None` | 优雅关闭调度器 |
| `get_job_status` | `(job_id: str) -> Optional[Dict[str, Any]]` | 获取单个任务状态 |
| `get_all_jobs` | `() -> List[Dict[str, Any]]` | 获取所有任务信息 |
| `remove_job` | `(job_id: str) -> None` | 移除已调度的任务 |
| `trigger_job` | `(job_id: str, **kwargs) -> None` | 立即触发一次任务执行 |

所有方法 SHALL 为 `async` 且使用 `@abstractmethod` 装饰器。Port 文件 SHALL NOT 包含任何 DTO 或实体定义。

#### Scenario: Port 接口完整性

- **WHEN** 审查 `SchedulerPort` 抽象基类
- **THEN** SHALL 包含上述全部 7 个抽象方法，签名与表中一致，无具体实现代码

#### Scenario: remove_job 在 Port 中定义

- **WHEN** `SchedulerApplicationService` 调用 `remove_job`
- **THEN** SHALL 直接通过 `self._scheduler_port.remove_job(job_id)` 调用，无需 `hasattr()` 检查

#### Scenario: trigger_job 在 Port 中定义

- **WHEN** `SchedulerApplicationService` 调用 `trigger_job`
- **THEN** SHALL 直接通过 `self._scheduler_port.trigger_job(job_id, **kwargs)` 调用，无需 `hasattr()` 检查

---

### Requirement: APScheduler 适配器实现

系统 SHALL 在 `src/modules/foundation/infrastructure/adapters/apscheduler_adapter.py` 中提供 `APSchedulerAdapter` 类，实现 `SchedulerPort` 的全部 7 个方法。适配器 SHALL 封装 APScheduler 的 `AsyncIOScheduler`，对外屏蔽框架细节。适配器 SHALL 以 Singleton 模式在 DI 容器中注册，确保全局只有一个调度器实例。

#### Scenario: 适配器实现完整性

- **WHEN** 审查 `APSchedulerAdapter` 类
- **THEN** SHALL 实现 `SchedulerPort` 的全部 7 个方法，包括 `remove_job` 和 `trigger_job`

#### Scenario: 任务不存在时 remove_job 抛出异常

- **WHEN** 调用 `remove_job` 传入不存在的 `job_id`
- **THEN** SHALL 抛出 `SchedulerJobNotFoundException`

#### Scenario: 任务不存在时 trigger_job 抛出异常

- **WHEN** 调用 `trigger_job` 传入不存在的 `job_id`
- **THEN** SHALL 抛出 `SchedulerJobNotFoundException`

---

### Requirement: SchedulerApplicationService 编排能力

系统 SHALL 在 `src/modules/foundation/application/services/scheduler_application_service.py` 中提供 `SchedulerApplicationService`，通过依赖注入接收 `SchedulerPort` 和 `SchedulerJobConfigRepositoryPort`。该服务 SHALL 承担以下编排职责：

1. **schedule_and_persist_job**：调度任务到调度器 + 持久化配置到数据库（原子编排）。
2. **stop_and_disable_job**：从调度器移除任务 + 更新数据库 `enabled=False`。
3. **trigger_job**：通过 Port 立即触发一次任务执行。
4. **query_execution_logs**：查询调度执行历史记录。
5. **load_persisted_jobs**：从数据库加载持久化配置并注册（已有方法，保持不变）。

Presentation 层（Routes）SHALL NOT 直接依赖任何 Repository 或 `get_async_session`，所有持久化操作 SHALL 通过 Application Service 完成。

#### Scenario: schedule_and_persist_job 原子编排

- **WHEN** 通过 REST API 启动一个新任务（Interval 或 Cron 模式）
- **THEN** `SchedulerApplicationService` SHALL 同时调度任务到 APScheduler 并持久化配置到 `scheduler_job_config` 表

#### Scenario: stop_and_disable_job 原子编排

- **WHEN** 通过 REST API 停止一个任务
- **THEN** `SchedulerApplicationService` SHALL 从 APScheduler 移除任务并将数据库中对应配置的 `enabled` 设为 `False`

#### Scenario: trigger_job 实际执行

- **WHEN** 通过 REST API 立即触发一个任务
- **THEN** `SchedulerApplicationService` SHALL 通过 `SchedulerPort.trigger_job()` 实际触发任务执行，而非返回伪响应

#### Scenario: query_execution_logs 查询

- **WHEN** 通过 REST API 查询执行历史
- **THEN** `SchedulerApplicationService` SHALL 通过 `SchedulerExecutionLogRepository`（由 DI 注入）返回执行记录，支持按 `job_id` 过滤和 `limit` 限制

#### Scenario: Routes 无 Repository 直接依赖

- **WHEN** 审查 `scheduler_routes.py` 的 import 列表
- **THEN** SHALL NOT 存在对 `SchedulerJobConfigRepository`、`SchedulerExecutionLogRepository`、`get_async_session` 的 import

---

### Requirement: Job 注册机制（模块声明 + 启动收集）

系统 SHALL 采用「模块声明 + 启动收集」模式管理 Job 注册。每个拥有调度任务的业务模块 SHALL 在其 `application/` 层定义 `job_registry.py`，导出 `get_job_registry() -> Dict[str, Callable]` 函数。`main.py` SHALL 在启动时从各模块 `application/` 层收集注册表，合并后传给 `SchedulerApplicationService.load_persisted_jobs()`。Foundation 模块自身 SHALL NOT import 任何业务模块。

#### Scenario: data_engineering 模块声明注册表

- **WHEN** 审查 `src/modules/data_engineering/application/job_registry.py`
- **THEN** SHALL 导出 `get_job_registry()` 函数，返回包含所有数据同步 Job 的 `Dict[str, Callable]` 映射

#### Scenario: main.py 从 Application 层收集

- **WHEN** 审查 `main.py` 的 Scheduler 启动流程
- **THEN** SHALL 从各模块的 `application/job_registry` 导入注册表（而非从 Presentation 层），合并后传给 `load_persisted_jobs()`

#### Scenario: Foundation 不依赖业务模块

- **WHEN** 审查 `src/modules/foundation/` 的全部 import
- **THEN** SHALL NOT 存在对 `src.modules.data_engineering`、`src.modules.research`、`src.modules.market_insight` 等业务模块的 import

---

### Requirement: Scheduler REST API

系统 SHALL 在 `src/modules/foundation/presentation/rest/scheduler_routes.py` 中提供以下 REST 端点：

| 端点 | 方法 | 职责 |
|------|------|------|
| `/scheduler/status` | GET | 获取调度器运行状态和已注册任务列表 |
| `/scheduler/jobs/{job_id}/start` | POST | 启动 Interval 模式定时任务 |
| `/scheduler/jobs/{job_id}/schedule` | POST | 启动 Cron 模式定时任务 |
| `/scheduler/jobs/{job_id}/trigger` | POST | 立即触发一次任务 |
| `/scheduler/jobs/{job_id}/stop` | POST | 停止并禁用任务 |
| `/scheduler/executions` | GET | 查询调度执行历史 |

所有端点 SHALL 仅通过 `SchedulerApplicationService`（DI 注入）完成业务逻辑，不直接操作 Repository 或数据库会话。响应模型 SHALL 定义在独立的 `scheduler_schemas.py` 文件中。

#### Scenario: Routes 通过 Application Service 操作

- **WHEN** 任意 Scheduler REST 端点被调用
- **THEN** SHALL 委托 `SchedulerApplicationService` 的对应方法执行，Routes 仅负责 HTTP 请求/响应映射

#### Scenario: 响应模型独立文件

- **WHEN** 审查 `presentation/rest/` 目录
- **THEN** SHALL 存在 `scheduler_schemas.py`，包含 `JobDetail`、`SchedulerStatusResponse`、`ExecutionLogDetail` 等 Pydantic Model 定义

---

### Requirement: Foundation DI 容器

系统 SHALL 在 `src/modules/foundation/infrastructure/di/container.py` 中配置 Foundation 模块的依赖注入容器。容器 SHALL 注册以下组件：

- `APSchedulerAdapter` — Singleton 模式（全局唯一调度器实例）
- `SchedulerPort` — 绑定到 `APSchedulerAdapter`
- `SchedulerJobConfigRepositoryPort` — 绑定到 `SchedulerJobConfigRepository`（通过工厂创建）
- `SchedulerApplicationService` — Factory 模式（注入 Port 和 Repository）

容器 SHALL 提供 `get_scheduler_service() -> SchedulerApplicationService` 工厂函数。原 `src/shared/infrastructure/di/container.py` 中的所有 Scheduler 相关配置 SHALL 被移除。

#### Scenario: DI 容器组件完整

- **WHEN** 通过 `get_scheduler_service()` 获取服务实例
- **THEN** 返回的 `SchedulerApplicationService` SHALL 已正确注入 `SchedulerPort` 和 `SchedulerJobConfigRepositoryPort`

#### Scenario: shared DI 清理

- **WHEN** 审查 `src/shared/infrastructure/di/container.py`
- **THEN** SHALL NOT 存在 `APSchedulerAdapter`、`SchedulerPort`、`SchedulerApplicationService` 等 Scheduler 相关的 provider 配置

---

### Requirement: Foundation 领域异常体系

系统 SHALL 在 `src/modules/foundation/domain/exceptions.py` 中定义 Scheduler 相关的领域异常。所有异常 SHALL 继承 `src.shared.domain.exceptions.AppException`。异常体系 SHALL 包含：

| 异常类 | 语义 |
|--------|------|
| `SchedulerException` | Scheduler 通用异常基类 |
| `SchedulerJobNotFoundException` | 任务不存在 |
| `SchedulerJobAlreadyExistsException` | 任务已存在 |
| `SchedulerConfigurationException` | 配置无效 |
| `SchedulerExecutionException` | 执行失败 |

`src/shared/domain/exceptions.py` SHALL 移除上述异常类，仅保留 `AppException` 和其他全局通用异常。

#### Scenario: 异常继承关系

- **WHEN** 审查 Foundation 的领域异常
- **THEN** 所有 Scheduler 异常 SHALL 继承 `AppException`，且全局异常处理中间件能正常捕获并转为 HTTP 响应

#### Scenario: shared 异常清理

- **WHEN** 审查 `src/shared/domain/exceptions.py`
- **THEN** SHALL NOT 包含 `SchedulerException`、`SchedulerJobNotFoundException`、`SchedulerJobAlreadyExistsException`、`SchedulerConfigurationException`、`SchedulerExecutionException`

---

### Requirement: 测试目录迁移

所有 Scheduler 相关测试 SHALL 迁移到 Foundation 模块的测试目录下：

- 单元测试：`tests/unit/modules/foundation/`
- 集成测试：`tests/integration/modules/foundation/`

迁移后所有测试 SHALL 更新 import 路径指向 `src.modules.foundation`，且通过 `pytest` 运行无错误。

#### Scenario: 单元测试迁移完整

- **WHEN** 运行 `pytest tests/unit/modules/foundation/ -v`
- **THEN** 原 `tests/unit/shared/test_scheduler_*` 的所有测试用例 SHALL 在新路径下全部通过

#### Scenario: 集成测试迁移完整

- **WHEN** 运行 `pytest tests/integration/modules/foundation/ -v`
- **THEN** 原 `tests/integration/shared/test_apscheduler_adapter.py` 的所有测试用例 SHALL 在新路径下全部通过
