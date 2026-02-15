## Why

当前 Scheduler 相关代码散落在 `src/shared/`（Domain Ports、Application Service、Infrastructure Adapters、DI Container）和 `src/modules/data_engineering/`（REST Routes、JOB_REGISTRY），存在三个架构问题：

1. **Shared Kernel 膨胀**：`src/shared/` 按 `vision-and-modules.md` 的约定仅应包含「高度通用、极少变更」的代码（如 `AppException`、`logger`），但 Scheduler 拥有完整的四层 DDD 结构（Port → Application Service → Infrastructure Adapter → DI Container），已是一个独立的支撑能力，不适合留在 Shared Kernel。
2. **Routes 归属错误**：`scheduler_routes.py` 放在 `data_engineering/presentation/rest/` 下，但其管理的是全局调度能力（任务 CRUD、触发、状态查询），不属于 Data Engineering 的 Bounded Context。
3. **DDD 违规**：`data_engineering` 的调度存在分层混乱——`JOB_REGISTRY` 定义在 Presentation 层并被 `main.py` 反向 import；Port 接口不完整（`remove_job`/`trigger_job` 在 Adapter 实现但 Port 未定义）；Repository 多处绕过 DI 直接实例化。

需要将 Scheduler 提取为独立模块 **Foundation**，作为公共支撑能力层，后续可承载消息推送等横切关注点。

## What Changes

- **新增 `foundation` 模块**（`src/modules/foundation/`）：作为公共支撑能力的 Bounded Context，首个能力为 Scheduler 服务。遵循标准 DDD 四层目录结构。
- **BREAKING**：将 `src/shared/` 中所有 Scheduler 相关代码（domain/ports、domain/dtos、domain/types、application/services、application/dtos、infrastructure/adapters、infrastructure/scheduler/、infrastructure/di/）迁移到 `src/modules/foundation/` 对应层级。
- **BREAKING**：将 `src/modules/data_engineering/presentation/rest/scheduler_routes.py` 迁移到 `src/modules/foundation/presentation/rest/`。
- **重构 Job 注册机制**：`JOB_REGISTRY` 从 Presentation 层提升到 Application 层，由 Foundation 模块的 Application Service 管理注册流程；`data_engineering` 等业务模块通过 Foundation 提供的注册接口声明自己的 Job，而非在 Presentation 层硬编码映射表。
- **补全 Port 接口**：`SchedulerPort` 补充 `remove_job()` 和 `trigger_job()` 方法定义，消除 `hasattr()` hack。
- **统一 DI 与会话管理**：所有 Repository 通过 DI 容器获取，消除手动实例化；统一数据库会话管理策略。
- **更新 `vision-and-modules.md`**：注册 Foundation 模块到模块注册表。
- **迁移测试**：将 `tests/unit/shared/test_scheduler_*` 和 `tests/integration/shared/test_apscheduler_adapter.py` 迁移到 `tests/unit/modules/foundation/` 和 `tests/integration/modules/foundation/` 下。

## Capabilities

### New Capabilities

- `foundation-scheduler-service`：Foundation 模块的调度器服务能力——完整的 DDD 四层结构（Domain Ports / Application Service / Infrastructure Adapter / Presentation REST）、Job 注册机制、DI 集成、以及各业务模块向 Foundation 声明调度任务的协作模式。

### Modified Capabilities

- `scheduler-persistence`：持久化代码从 `src/shared/infrastructure/scheduler/` 迁移到 `src/modules/foundation/infrastructure/`，涉及路径引用、DI 容器配置、以及 Repository 获取方式的变更。Spec 中的功能需求不变，但实现归属模块变更。

## Impact

- **代码迁移**：约 15+ 文件从 `src/shared/` 和 `src/modules/data_engineering/` 移入 `src/modules/foundation/`；`src/shared/` 中 Scheduler 相关目录清空。
- **Import 路径变更（BREAKING）**：所有 import `src.shared.domain.ports.scheduler_port`、`src.shared.application.services.scheduler_service` 等路径的代码需更新。受影响模块：`main.py`、`data_engineering`。
- **DI 容器重构**：`src/shared/infrastructure/di/container.py` 中的 Scheduler 相关配置迁移到 Foundation 模块自己的 DI 配置中。
- **`main.py` 启动流程调整**：Scheduler 初始化从直接调用 shared DI 改为通过 Foundation 模块的 Application Service。
- **`data_engineering` 精简**：移除 `scheduler_routes.py`；Job 函数（`sync_scheduler.py`、`akshare_market_data_jobs.py`）保留在 `data_engineering` 中（它们是数据同步领域逻辑），但注册方式改为通过 Foundation 提供的接口。
- **测试迁移**：7 个测试文件需迁移目录并更新 import 路径。
- **Spec 文档**：`vision-and-modules.md` 模块注册表新增 Foundation 条目。
