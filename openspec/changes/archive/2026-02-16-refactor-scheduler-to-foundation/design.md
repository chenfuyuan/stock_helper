## Context

### 现状

Scheduler 相关代码分布在三个位置：

1. **`src/shared/`** — 拥有完整的四层 DDD 结构（Domain Ports、Application Service、Infrastructure Adapter、DI Container），已远超 Shared Kernel 的定位。
2. **`src/modules/data_engineering/presentation/rest/scheduler_routes.py`** — 全局调度 REST API + `JOB_REGISTRY` 硬编码映射表，不属于 Data Engineering 的业务边界。
3. **`src/main.py`** — 反向 import `data_engineering` Presentation 层的 `JOB_REGISTRY`，违反分层原则。

### 约束

- 本项目采用模块化单体架构，模块间通过 Application 层接口通信。
- 已有 `scheduler-persistence` spec 定义了持久化能力，功能需求不变。
- `data_engineering` 的 Job 函数（`sync_scheduler.py`、`akshare_market_data_jobs.py`）是数据同步领域逻辑，应保留在该模块中。
- APScheduler 作为唯一调度框架，短期内不会更换。

---

## Goals / Non-Goals

**Goals:**

- G1：建立 `src/modules/foundation/` 模块，作为公共支撑能力的 Bounded Context，遵循标准 DDD 四层结构。
- G2：将 Scheduler 全部能力从 `src/shared/` 和 `data_engineering` 迁移到 Foundation 模块，使 `src/shared/` 恢复 Shared Kernel 的纯净定位。
- G3：补全 `SchedulerPort` 接口（`remove_job`、`trigger_job`），消除 `hasattr()` hack。
- G4：重构 Job 注册机制，使注册表归属清晰、分层合理，消除 `main.py` 对 Presentation 层的反向依赖。
- G5：统一 Repository 获取方式（全部通过 DI），消除 `scheduler_routes.py` 中手动实例化 Repository 的违规操作。
- G6：迁移所有 Scheduler 相关测试到 `tests/*/modules/foundation/` 目录结构下。

**Non-Goals:**

- NG1：不引入新的调度框架或替换 APScheduler。
- NG2：不改变 Scheduler 的功能需求（持久化模型、启动加载、执行跟踪等逻辑不变）。
- NG3：不实现 Foundation 的其他支撑能力（如消息推送），仅搭建模块骨架并安置 Scheduler。
- NG4：不修改 `data_engineering` 的 Job 函数实现逻辑，仅调整其注册方式。
- NG5：不改变数据库表结构（`scheduler_job_config`、`scheduler_execution_log` 表不变）。

---

## Decisions

### D1：Foundation 模块目录结构

**决策**：在 `src/modules/foundation/` 下建立标准 DDD 四层结构，Scheduler 作为首个子能力。

```
src/modules/foundation/
├── __init__.py
├── application/
│   ├── __init__.py
│   ├── services/
│   │   ├── __init__.py
│   │   └── scheduler_application_service.py
│   └── dtos/
│       ├── __init__.py
│       └── scheduler_dtos.py
├── domain/
│   ├── __init__.py
│   ├── ports/
│   │   ├── __init__.py
│   │   ├── scheduler_port.py
│   │   └── scheduler_job_config_repository_port.py
│   ├── dtos/
│   │   ├── __init__.py
│   │   └── scheduler_dtos.py
│   ├── types.py
│   └── exceptions.py
├── infrastructure/
│   ├── __init__.py
│   ├── adapters/
│   │   ├── __init__.py
│   │   └── apscheduler_adapter.py
│   ├── persistence/
│   │   ├── __init__.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── scheduler_job_config_model.py
│   │   │   └── scheduler_execution_log_model.py
│   │   └── repositories/
│   │       ├── __init__.py
│   │       ├── scheduler_job_config_repo.py
│   │       ├── scheduler_job_config_repo_factory.py
│   │       └── scheduler_execution_log_repo.py
│   ├── execution_tracker.py
│   └── di/
│       ├── __init__.py
│       └── container.py
└── presentation/
    └── rest/
        ├── __init__.py
        ├── scheduler_routes.py
        └── scheduler_schemas.py
```

**理由**：
- 符合 `tech-standards.md` 的模块内部结构模板。
- `persistence/` 替代原 `scheduler/` 子目录，语义更清晰。
- `presentation/rest/scheduler_schemas.py` 将 Routes 中内联定义的 Pydantic Model（`JobDetail`、`SchedulerStatusResponse`、`ExecutionLogDetail`）提取为独立文件，符合 SRP。

**备选**：将 Scheduler 保留在 `src/shared/` 但增加子包隔离 → 拒绝，因为 Shared Kernel 不应承载具备完整 DDD 分层的独立能力。

### D2：Job 注册机制重构

**决策**：采用「模块声明 + 启动收集」模式。

1. 每个拥有 Job 的业务模块在 **`application/`** 层定义 `job_registry.py`，导出一个 `get_job_registry() -> Dict[str, Callable]` 函数。
2. `main.py` 在启动时从各模块 `application/` 层收集注册表，合并后传给 Foundation 的 `SchedulerApplicationService.load_persisted_jobs()`。
3. Foundation 自身不 import 任何业务模块，Job 函数映射完全由调用方提供。

```python
# src/modules/data_engineering/application/job_registry.py
from src.modules.data_engineering.presentation.jobs.sync_scheduler import (...)
from src.modules.data_engineering.presentation.jobs.akshare_market_data_jobs import (...)

def get_job_registry() -> dict[str, Callable]:
    """Data Engineering 模块的调度任务注册表"""
    return {
        "sync_daily_history": sync_history_daily_data_job,
        "sync_daily_by_date": sync_daily_data_job,
        ...
    }
```

```python
# src/main.py (启动时)
from src.modules.data_engineering.application.job_registry import get_job_registry as de_registry
from src.modules.foundation.infrastructure.di.container import get_scheduler_service

scheduler_service = get_scheduler_service()
await scheduler_service.start_scheduler()

# 收集各模块的 Job 注册表
combined_registry = {**de_registry()}
await scheduler_service.load_persisted_jobs(combined_registry)
```

**理由**：
- 依赖方向合规：`main.py`（编排层）→ `data_engineering.application`（应用层），不穿透到 Presentation。
- Foundation 不依赖任何业务模块，保持支撑层独立性。
- 扩展简单：新模块只需导出 `get_job_registry()` 并在 `main.py` 中注册。

**备选方案（拒绝）**：
- **Provider 抽象**：Foundation 定义 `JobRegistryProvider` Port，各模块实现 → 当前规模过度设计，引入不必要的抽象层。等模块超过 5 个再考虑自动发现。
- **全局注册表 Singleton**：各模块启动时主动 push 到全局 dict → 隐式依赖，难以追踪注册来源。

### D3：SchedulerPort 接口补全

**决策**：在 `SchedulerPort` 中增加 `remove_job()` 和 `trigger_job()` 抽象方法。

```python
class SchedulerPort(ABC):
    # ... 现有方法 ...

    @abstractmethod
    async def remove_job(self, job_id: str) -> None:
        """移除已调度的任务"""
        pass

    @abstractmethod
    async def trigger_job(self, job_id: str, **kwargs) -> None:
        """立即触发一次任务执行"""
        pass
```

**理由**：
- `APSchedulerAdapter` 已实现这两个方法，但 Port 未声明，导致 `SchedulerApplicationService.remove_job()` 使用 `hasattr()` 检查——这违反了依赖倒置原则。
- Port 应完整描述调度器的全部能力契约。

### D4：DI 容器归属

**决策**：Foundation 模块拥有自己的 DI 容器（`src/modules/foundation/infrastructure/di/container.py`），提供 `get_scheduler_service()` 等工厂函数。原 `src/shared/infrastructure/di/container.py` 中的 Scheduler 相关配置全部迁出。

**理由**：
- 与现有模式一致（`knowledge_center` 已有独立 container）。
- `src/shared/infrastructure/di/` 清空 Scheduler 配置后，如无其他用途则保留为空或移除。

**备选**：保留 `src/shared/infrastructure/di/` 作为中央 DI 注册点 → 拒绝，会导致 shared 再次膨胀。

### D5：Presentation 层 — Routes 迁移与 DTO 整理

**决策**：

1. `scheduler_routes.py` 整体迁入 `foundation/presentation/rest/`。
2. 路由内联的 Pydantic Model（`JobDetail`、`SchedulerStatusResponse`、`ExecutionLogDetail`）提取到 `scheduler_schemas.py`。
3. Routes 中手动实例化 Repository 的代码改为通过 DI 获取或委托 Application Service。具体而言：
   - `start_job` / `schedule_job` 中的持久化操作（`repo.upsert()`）下沉到 `SchedulerApplicationService`。
   - `stop_job` 中的 `repo.update_enabled()` 同样下沉到 Application Service。
   - `get_executions` 的查询通过 Application Service 的查询方法完成。
   - `trigger_job` 端点调用 `SchedulerApplicationService.trigger_job()` 而非返回假响应。
4. Routes 不再直接 import 任何 Repository 或 `get_async_session`。

**理由**：
- 消除 Presentation 层对 Infrastructure 的直接依赖。
- Application Service 统一负责业务编排（调度 + 持久化），Routes 只做 HTTP 映射。

### D6：Scheduler 异常保留在 `src/shared/domain/exceptions.py`

**决策**：`SchedulerException` 及其子类（`SchedulerJobNotFoundException`、`SchedulerJobAlreadyExistsException`、`SchedulerConfigurationException`、`SchedulerExecutionException`）**迁移**到 `src/modules/foundation/domain/exceptions.py`。

`src/shared/domain/exceptions.py` 仅保留 `AppException` 基类和其他全局通用异常。

**理由**：
- Scheduler 异常是 Foundation 模块的领域异常，属于该 Bounded Context。
- 符合「模块异常放在模块 `domain/exceptions.py`」的约定。
- Foundation 的异常仍继承 `src/shared/domain/exceptions.AppException`，保持异常处理中间件的兼容性。

---

## Risks / Trade-offs

### R1：Import 路径全局变更

- **风险**：所有 `from src.shared.domain.ports.scheduler_port import ...` 等路径需批量更新，遗漏会导致 `ImportError`。
- **缓解**：使用 IDE 全局搜索 + 替换；迁移完成后运行 `python -c "import src.modules.foundation"` 验证；CI 中 `mypy` / `flake8` 检查可捕获遗漏。

### R2：Git 历史断裂

- **风险**：文件从 `src/shared/` 移动到 `src/modules/foundation/` 可能导致 Git blame 历史丢失。
- **缓解**：使用 `git mv` 移动文件，Git 可追踪 rename；分多次原子提交（先移动再修改），确保 diff 可读。

### R3：`main.py` 启动顺序依赖

- **风险**：Foundation DI 初始化顺序与数据库会话可用性之间的时序耦合。
- **缓解**：Foundation 的 `SchedulerJobConfigRepositoryFactory` 继续采用 lazy 创建 session 的模式；`load_persisted_jobs()` 已有 graceful degradation（失败不阻塞启动）。

### R4：测试迁移遗漏

- **风险**：测试文件迁移后 import 路径未更新，导致测试跳过或报错。
- **缓解**：迁移后立即运行 `pytest tests/unit/modules/foundation/ tests/integration/modules/foundation/ -v` 验证。

---

## Migration Plan

### Phase 1：创建 Foundation 模块骨架

1. 创建 `src/modules/foundation/` 完整目录结构（含 `__init__.py`）。
2. 更新 `vision-and-modules.md` 注册 Foundation 模块。

### Phase 2：代码迁移（使用 `git mv`）

1. 迁移 Domain 层：`scheduler_port.py`、`scheduler_job_config_repository_port.py`、`scheduler_dtos.py`、`types.py`。
2. 迁移 Domain 异常：从 `src/shared/domain/exceptions.py` 提取 Scheduler 异常到 `foundation/domain/exceptions.py`。
3. 迁移 Application 层：`scheduler_service.py`、`scheduler_dtos.py`（application 层）。
4. 迁移 Infrastructure 层：`apscheduler_adapter.py`、全部 persistence 代码、`execution_tracker.py`、DI container。
5. 迁移 Presentation 层：`scheduler_routes.py`，提取 schemas。

### Phase 3：接口补全与重构

1. `SchedulerPort` 补充 `remove_job()`、`trigger_job()` 定义。
2. `SchedulerApplicationService` 增加 `upsert_and_schedule_job()`、`stop_and_disable_job()`、`query_execution_logs()` 等方法，将 Routes 中的持久化逻辑下沉。
3. `scheduler_routes.py` 简化为纯 HTTP 映射，移除所有 Repository 直接引用。

### Phase 4：Job 注册机制重构

1. 在 `data_engineering/application/` 下创建 `job_registry.py`。
2. 更新 `main.py`：从各模块 application 层收集注册表。

### Phase 5：清理与验证

1. 删除 `src/shared/` 中已迁出的 Scheduler 相关文件和目录。
2. 清理 `src/shared/infrastructure/di/container.py`（移除 Scheduler 配置）。
3. 迁移测试文件到 `tests/*/modules/foundation/`。
4. 全量运行测试验证。
5. 运行 `mypy` / `flake8` 确保无 import 错误。

### Rollback

- 每个 Phase 对应一个原子 Git commit。
- 如需回滚，`git revert` 对应 Phase 的 commit 即可。
- 数据库无 schema 变更，不需要回滚 migration。

---

## Open Questions

- **OQ1**：`src/shared/infrastructure/di/container.py` 清空 Scheduler 配置后是否还有其他内容？如果为空，是否直接删除该文件？→ 需检查是否有其他模块依赖此容器。
- **OQ2**：`data_engineering/presentation/jobs/` 下的 Job 函数目前直接使用 `AsyncSessionLocal()` 创建数据库会话。是否应在本次变更中统一为 DI 注入？→ 建议作为 follow-up 优化，本次保持不动以控制变更范围。
