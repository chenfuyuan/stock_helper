## 1. Foundation 模块骨架与规范更新

- [x] 1.1 创建 `src/modules/foundation/` 完整目录结构（含所有子包的 `__init__.py`）：`application/services/`、`application/dtos/`、`domain/ports/`、`domain/dtos/`、`infrastructure/adapters/`、`infrastructure/persistence/models/`、`infrastructure/persistence/repositories/`、`infrastructure/di/`、`presentation/rest/`
- [x] 1.2 更新 `openspec/specs/vision-and-modules.md` 模块注册表（§4.2），新增 Foundation 模块条目

## 2. Domain 层迁移与补全

- [x] 🔴 2.1 编写 `SchedulerPort` 完整接口测试（验证 7 个抽象方法存在、`remove_job`/`trigger_job` 可直接调用无需 `hasattr`）→ `tests/unit/modules/foundation/test_scheduler_port.py`
- [x] 2.2 使用 `git mv` 将 `src/shared/domain/ports/scheduler_port.py` 迁移到 `src/modules/foundation/domain/ports/scheduler_port.py`，补充 `remove_job()` 和 `trigger_job()` 抽象方法定义，更新 import 路径
- [x] 2.3 使用 `git mv` 将 `src/shared/domain/ports/scheduler_job_config_repository_port.py` 迁移到 `src/modules/foundation/domain/ports/`，更新 import 路径
- [x] 2.4 使用 `git mv` 将 `src/shared/domain/dtos/scheduler_dtos.py` 迁移到 `src/modules/foundation/domain/dtos/`，更新 import 路径
- [x] 2.5 使用 `git mv` 将 `src/shared/domain/types.py` 迁移到 `src/modules/foundation/domain/types.py`，更新 import 路径
- [x] 🔴 2.6 编写 Foundation 领域异常测试（继承 `AppException`、各异常类存在）→ `tests/unit/modules/foundation/test_scheduler_exceptions.py`
- [x] 2.7 在 `src/modules/foundation/domain/exceptions.py` 中创建 Scheduler 异常体系（`SchedulerException` 及 4 个子类），继承 `AppException`
- [x] 2.8 从 `src/shared/domain/exceptions.py` 移除 `SchedulerException` 及其子类，仅保留 `AppException` 和其他全局通用异常

## 3. Application 层迁移与重构

- [x] 🔴 3.1 编写 `SchedulerApplicationService` 新增方法测试（`schedule_and_persist_job`、`stop_and_disable_job`、`trigger_job`、`query_execution_logs`，Mock Port 和 Repository）→ `tests/unit/modules/foundation/test_scheduler_application_service.py`
- [x] 3.2 使用 `git mv` 将 `src/shared/application/services/scheduler_service.py` 迁移到 `src/modules/foundation/application/services/scheduler_application_service.py`，更新 import 路径
- [x] 3.3 在 `SchedulerApplicationService` 中新增 `schedule_and_persist_job()` 方法（调度 + 持久化原子编排），替代原 Routes 中的内联持久化逻辑
- [x] 3.4 在 `SchedulerApplicationService` 中新增 `stop_and_disable_job()` 方法（移除任务 + 更新 DB enabled=False）
- [x] 3.5 在 `SchedulerApplicationService` 中新增 `trigger_job()` 方法（通过 `SchedulerPort.trigger_job()` 实际触发任务）
- [x] 3.6 在 `SchedulerApplicationService` 中新增 `query_execution_logs()` 方法（通过 DI 注入的 Repository 查询执行历史）
- [x] 3.7 移除 `SchedulerApplicationService.remove_job()` 中的 `hasattr()` hack，直接调用 `self._scheduler_port.remove_job()`
- [x] 3.8 使用 `git mv` 将 `src/shared/application/dtos/scheduler_dtos.py` 迁移到 `src/modules/foundation/application/dtos/`，更新 import 路径
- [x] 🔴 3.9 编写 Domain DTO 测试（迁移已有 `test_scheduler_dtos.py` 并更新 import）→ `tests/unit/modules/foundation/test_scheduler_dtos.py`

## 4. Infrastructure 层迁移

- [x] 4.1 使用 `git mv` 将 `src/shared/infrastructure/adapters/apscheduler_adapter.py` 迁移到 `src/modules/foundation/infrastructure/adapters/`，更新 import 路径（引用新的 `SchedulerPort`、异常、类型）
- [x] 4.2 使用 `git mv` 将 `src/shared/infrastructure/scheduler/models/` 下的 ORM 模型迁移到 `src/modules/foundation/infrastructure/persistence/models/`
- [x] 4.3 使用 `git mv` 将 `src/shared/infrastructure/scheduler/repositories/` 下的所有 Repository 迁移到 `src/modules/foundation/infrastructure/persistence/repositories/`，更新 import 路径
- [x] 4.4 使用 `git mv` 将 `src/shared/infrastructure/scheduler/execution_tracker.py` 迁移到 `src/modules/foundation/infrastructure/execution_tracker.py`，更新 import 路径
- [x] 4.5 在 `src/modules/foundation/infrastructure/di/container.py` 创建 Foundation DI 容器（注册 `APSchedulerAdapter` Singleton、Port 绑定、Repository Factory、`SchedulerApplicationService` Factory），提供 `get_scheduler_service()` 工厂函数
- [x] 4.6 迁移集成测试：使用 `git mv` 将 `tests/integration/shared/test_apscheduler_adapter.py` 迁移到 `tests/integration/modules/foundation/`，更新 import 路径并验证通过

## 5. Presentation 层迁移与重构

- [x] 5.1 从 `src/modules/data_engineering/presentation/rest/scheduler_routes.py` 中提取 `JobDetail`、`SchedulerStatusResponse`、`ExecutionLogDetail` 到 `src/modules/foundation/presentation/rest/scheduler_schemas.py`
- [x] 5.2 使用 `git mv` 将 `scheduler_routes.py` 迁移到 `src/modules/foundation/presentation/rest/scheduler_routes.py`
- [x] 5.3 重构 `scheduler_routes.py`：移除所有对 `SchedulerJobConfigRepository`、`SchedulerExecutionLogRepository`、`get_async_session` 的直接 import 和使用
- [x] 5.4 重构 `start_job` 和 `schedule_job` 端点：委托 `SchedulerApplicationService.schedule_and_persist_job()` 替代内联持久化
- [x] 5.5 重构 `stop_job` 端点：委托 `SchedulerApplicationService.stop_and_disable_job()` 替代内联 Repository 操作
- [x] 5.6 重构 `trigger_job` 端点：委托 `SchedulerApplicationService.trigger_job()` 实际触发任务，替代伪响应
- [x] 5.7 重构 `get_executions` 端点：委托 `SchedulerApplicationService.query_execution_logs()` 替代直接 Repository 查询
- [x] 5.8 更新 `src/api/routes.py`（或对应路由注册文件）：将 scheduler router 从 `data_engineering` 的路由注册改为从 Foundation 模块导入

## 6. Job 注册机制重构

- [x] 6.1 创建 `src/modules/data_engineering/application/job_registry.py`，导出 `get_job_registry() -> Dict[str, Callable]`，包含所有数据同步 Job 的映射
- [x] 6.2 更新 `src/main.py`：从 `src.modules.foundation.infrastructure.di.container` 导入 `get_scheduler_service`，从 `src.modules.data_engineering.application.job_registry` 导入 `get_job_registry`
- [x] 6.3 更新 `src/main.py` 的 `lifespan()` 函数：使用合并的注册表调用 `load_persisted_jobs()`，移除对 Presentation 层 `JOB_REGISTRY` 的导入

## 7. 清理与验证

- [x] 7.1 删除 `src/shared/` 中已迁出的 Scheduler 相关文件和空目录：`domain/ports/scheduler_port.py`、`domain/ports/scheduler_job_config_repository_port.py`、`domain/dtos/scheduler_dtos.py`、`domain/types.py`、`application/services/scheduler_service.py`、`application/dtos/scheduler_dtos.py`、`infrastructure/adapters/apscheduler_adapter.py`、`infrastructure/scheduler/`（整个目录）、`infrastructure/di/`（清理或删除）
- [x] 7.2 删除 `src/modules/data_engineering/presentation/rest/scheduler_routes.py`（确认已迁移到 Foundation）
- [x] 7.3 清理 `src/shared/infrastructure/di/container.py`：移除所有 Scheduler 相关的 provider 配置和 import
- [x] 7.4 删除 `tests/unit/shared/` 和 `tests/integration/shared/` 中已迁移的 Scheduler 测试文件
- [x] 7.5 全局搜索验证：确认无残留的 `from src.shared.domain.ports.scheduler_port`、`from src.shared.application.services.scheduler_service`、`from src.shared.infrastructure.di.container import get_scheduler_service` 等旧路径 import
- [x] 7.6 运行 `pytest tests/unit/modules/foundation/ tests/integration/modules/foundation/ -v`，验证所有 Foundation 测试通过
- [x] 7.7 运行全量测试 `docker compose exec app pytest`，确保无回归
- [x] 7.8 运行静态分析（`flake8` / `mypy`），确保无 import 错误或类型问题
