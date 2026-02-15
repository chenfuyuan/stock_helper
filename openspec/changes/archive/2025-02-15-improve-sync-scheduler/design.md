## Context

当前系统的定时任务调度基于 APScheduler（`AsyncIOScheduler`），`SchedulerService` 作为单例封装在 `src/shared/infrastructure/scheduler.py`。调度器在 `main.py` 的 lifespan 中启动，但仅启动框架本身——不注册任何 job。所有 job 的注册依赖 `scheduler_routes.py` 中的 HTTP 端点（`/start`、`/schedule`、`/trigger`），完全是内存态，重启即丢失。

TuShare 限速采用全局 `asyncio.Lock` + 固定间隔（`TUSHARE_MIN_INTERVAL=0.35s`，约 171 次/分钟），距离 200 次/分钟的上限有约 15% 的浪费。且缺少对 TuShare 返回"调用频率过高"异常的处理——直接抛出 `AppException` 并中断同步。

`SyncEngine` 的互斥检查仅判断 `status == RUNNING`，不考虑 `updated_at` 的时效性。进程崩溃后状态卡死，只能手动修数据库。

### 现有相关代码位置

| 组件 | 路径 |
|------|------|
| SchedulerService | `src/shared/infrastructure/scheduler.py` |
| Scheduler REST API | `src/modules/data_engineering/presentation/rest/scheduler_routes.py` |
| Job Functions | `src/modules/data_engineering/presentation/jobs/sync_scheduler.py` |
| SyncEngine | `src/modules/data_engineering/application/commands/sync_engine.py` |
| SyncTask 实体 | `src/modules/data_engineering/domain/model/sync_task.py` |
| TushareClient 限速 | `src/modules/data_engineering/infrastructure/external_apis/tushare/client.py` |
| DE 模块配置 | `src/modules/data_engineering/infrastructure/config.py` |
| 应用启动入口 | `src/main.py` |

---

## Goals / Non-Goals

**Goals:**

1. 应用启动后，预置的调度任务自动运行，无需人工干预（"部署即运行"）
2. 每次调度执行的启停时间、结果、错误信息持久化到数据库，支持查询
3. TuShare API 调用吞吐量接近 200 次/分钟上限，且在遇到频率超限响应时自动退避重试
4. RUNNING 状态的僵死任务能被自动检测并恢复，不阻塞新任务

**Non-Goals:**

- 不引入分布式调度框架（如 Celery、Airflow）——当前单实例部署，APScheduler 足够
- 不实现调度任务的 Web UI 管理界面
- 不做跨模块的通用调度抽象——目前仅 DE 模块使用调度器
- 不修改 APScheduler 的 JobStore 机制——使用自定义表而非 APScheduler 内置的 SQLAlchemy JobStore

---

## Decisions

### Decision 1: 调度配置持久化——自定义表 vs APScheduler 内置 JobStore

**选择：自定义 `scheduler_job_config` 表**

| 维度 | APScheduler SQLAlchemy JobStore | 自定义表 |
|------|---------------------------------|----------|
| 实现成本 | 低（配置一行代码） | 中（需建表 + Repository） |
| Schema 控制 | APScheduler 控制，字段固定（pickle 序列化 job） | 完全自控，字段语义化 |
| 可读性 | 差（pickle blob，人工不可读） | 好（cron_expression、enabled 等明确字段） |
| 与 DDD 对齐 | 差（绕过 Domain 层） | 好（有 Port、Repository、Entity） |
| 执行日志 | 无 | 可一并设计 |

**理由**：APScheduler 的 JobStore 将 job 对象序列化为 pickle，不可读且无法扩展执行日志。自定义表虽多写些代码，但与项目的 DDD 架构一致，且能精确控制字段（如 `enabled`、`timezone`、`last_run_at`），方便后续扩展。

### Decision 2: 调度持久化的模块归属——Shared vs DE

**选择：放在 `src/shared/infrastructure/scheduler/`**

**理由**：

- `SchedulerService` 已经在 `src/shared/` 中，调度配置持久化是其自然延伸
- `src/shared/infrastructure/persistence/` 已有 `external_api_call_log_model.py` 的先例——共享基础设施的持久化模型放在此处是已有模式
- 虽然当前只有 DE 模块使用调度器，但调度本身是通用基础设施能力，不应绑定到特定业务模块
- 具体的 job 函数（`sync_scheduler.py`）和 job 注册表（`JOB_REGISTRY`）仍留在 DE 模块——它们是业务代码

**目录结构**：

```
src/shared/infrastructure/scheduler/
├── __init__.py
├── scheduler_service.py        # 现有 SchedulerService 迁移至此
├── models/
│   ├── scheduler_job_config_model.py    # SQLAlchemy ORM
│   └── scheduler_execution_log_model.py # SQLAlchemy ORM
├── repositories/
│   ├── scheduler_job_config_repo.py     # Repository 实现
│   └── scheduler_execution_log_repo.py  # Repository 实现
└── execution_tracker.py        # 执行日志装饰器/上下文管理器
```

### Decision 3: 自动注册机制——启动时机与 Job 发现

**选择：启动时从 DB 加载 + 模块注册表匹配**

**流程**：

1. Alembic migration 在首次部署时 seed 默认调度配置（4 条记录，`enabled=True`）
2. `main.py` lifespan 中，在 `SchedulerService.start()` 之后调用新方法 `SchedulerService.load_persisted_jobs()`
3. `load_persisted_jobs()` 从 DB 读取所有 `enabled=True` 的配置
4. 对每条配置，通过 `job_id` 在各模块的 `JOB_REGISTRY` 中查找对应的 job 函数
5. 用配置中的 cron 表达式注册到 APScheduler

**Job 发现方式**：保留现有的 `JOB_REGISTRY` dict 模式。`load_persisted_jobs()` 接受一个 `registry: Dict[str, Callable]` 参数，由调用方（`main.py` 或模块注册入口）传入。这避免了 `src/shared/` 反向依赖 `src/modules/`。

**HTTP API 变更**：现有的 `/start`、`/schedule`、`/stop` 端点在操作 APScheduler 的同时，通过 Repository 将配置同步到 DB（upsert 语义）。这样下次重启自动生效。

### Decision 4: 执行日志记录——装饰器模式

**选择：上下文管理器（context manager）包裹 job 执行**

```python
async with ExecutionTracker(job_id="sync_daily_by_date", repo=execution_log_repo):
    await actual_job_function()
```

**理由**：

- 比装饰器更灵活，可以在 `sync_scheduler.py` 的 job 函数内部使用，不需要改函数签名
- 自动记录 start_time；正常退出记录 SUCCESS + end_time；异常时记录 FAILED + error_message + end_time
- 执行日志的写入失败不应中断主流程（`try/except` 保护）

### Decision 5: 滑动窗口限速器——替换固定间隔

**选择：Sliding Window Log（精确时间戳队列）**

**对比**：

| 算法 | 精确性 | 突发处理 | 复杂度 | 内存 |
|------|--------|---------|--------|------|
| 固定间隔（当前） | 过度保守 | 无突发，均匀分布 | 低 | O(1) |
| Token Bucket | 允许突发 | 突发后匀速补充 | 中 | O(1) |
| Sliding Window Log | 精确 | 允许突发，窗口内严格不超限 | 中 | O(N) |
| Sliding Window Counter | 近似 | 边界处有误差 | 低 | O(1) |

**选择理由**：

- **精确性**：TuShare 的 200 次/分钟是硬限制，近似算法有超限风险。Sliding Window Log 通过维护精确时间戳确保不超限。
- **突发友好**：批量同步场景中，一批完成后可能有短暂空闲，下一批启动时应能以最快速度调用。固定间隔做不到这一点。
- **内存可控**：窗口内最多 200 个时间戳（`float`），内存开销可忽略。
- **实现简洁**：一个 `collections.deque` + `asyncio.Lock` 即可。

**实现要点**：

```python
class SlidingWindowRateLimiter:
    def __init__(self, max_calls: int = 195, window_seconds: float = 60.0):
        self._max_calls = max_calls       # 预留 5 次安全余量
        self._window = window_seconds
        self._timestamps: deque[float] = deque()
        self._lock = asyncio.Lock()

    async def acquire(self):
        async with self._lock:
            now = time.monotonic()
            # 清除窗口外的旧时间戳
            while self._timestamps and now - self._timestamps[0] >= self._window:
                self._timestamps.popleft()
            # 若已达上限，等待最早的时间戳滑出窗口
            if len(self._timestamps) >= self._max_calls:
                wait = self._window - (now - self._timestamps[0])
                await asyncio.sleep(wait)
                self._timestamps.popleft()
            self._timestamps.append(time.monotonic())
```

**配置项**：`TUSHARE_RATE_LIMIT_MAX_CALLS`（默认 195）、`TUSHARE_RATE_LIMIT_WINDOW_SECONDS`（默认 60）。

### Decision 6: TuShare 频率超限异常处理——指数退避重试

**选择：在 `_rate_limited_call` 内部捕获并重试**

**策略**：

- 捕获 TuShare 返回的频率超限异常（通常包含 "抱歉，您每分钟最多访问该接口" 或类似关键词）
- 第 1 次重试等待 3 秒，第 2 次 6 秒，第 3 次 12 秒（指数退避，base=3s，factor=2）
- 超过 3 次重试后抛出原始异常，由上层处理
- 每次重试时记录 WARNING 日志

**理由**：封装在 `_rate_limited_call` 内部，对上层 UseCase 透明。滑动窗口限速器应能避免绝大多数频率超限，此处仅作为安全兜底。

### Decision 7: 僵死任务检测——`updated_at` + 超时阈值

**选择：在互斥检查时内联检测，不引入独立的守护进程**

**逻辑（修改 `SyncEngine.run_history_sync` 的互斥检查部分）**：

```
查到 latest_task 且 status == RUNNING:
  if now - updated_at > STALE_TIMEOUT:
    → 标记为 FAILED（记录 "超时自动标记" 原因）
    → 允许创建新任务
  else:
    → 拒绝启动（现有行为）
```

**超时阈值**：`SYNC_TASK_STALE_TIMEOUT_MINUTES`，默认 10 分钟。

**为什么 10 分钟**：
- 当前历史同步每批处理约 50 只股票，每只股票的 TuShare 调用约 3 次（daily + adj_factor + daily_basic），每次调用约 0.3s
- 一批最长约 50 × 3 × 0.35s ≈ 52.5s，加上 DB 写入开销，一批约 1-2 分钟
- 10 分钟意味着至少 5 批没有更新，足以判定为僵死
- 此值可配置，用户可根据实际情况调整

**`updated_at` 覆盖检查**：
- `SyncTask.update_progress()` 已更新 `updated_at` ✓
- `SyncTask.start()` 已更新 `updated_at` ✓
- 需确认 `SyncEngine` 中每批完成后 `await self.sync_task_repo.update(task)` 确实写入 DB ✓（当前逻辑已覆盖）

---

## Risks / Trade-offs

### [Risk] 滑动窗口限速器的 `asyncio.sleep` 可能不够精确
**→ 缓解**：预留 5 次/分钟的安全余量（195 vs 200）。即使 sleep 有轻微误差（通常 < 10ms），也不会超限。实际部署后可根据日志监控调整 `max_calls`。

### [Risk] TuShare 频率超限异常的关键词匹配可能不稳定
**→ 缓解**：使用宽泛的关键词匹配（如包含 "频率" 或 "每分钟" 或 HTTP 状态码），并在 `except Exception` 层面兜底记录日志。如果 TuShare 修改了错误消息格式，至少不会吞掉异常。

### [Risk] 启动时 DB 不可用导致调度加载失败
**→ 缓解**：`load_persisted_jobs()` 用 `try/except` 包裹，失败时记录 ERROR 日志但不阻止应用启动。此时退化为"手动注册"模式（与当前行为一致）。

### [Risk] 多实例部署时的调度重复执行
**→ 接受**：当前为单实例部署，暂不处理。如果未来需要多实例，可引入分布式锁或切换到 Celery Beat。在 `scheduler_job_config` 表中预留 `instance_id` 字段备用。

### [Trade-off] 自定义持久化 vs APScheduler JobStore
**→ 接受**：多写约 200 行代码，换来完全可控的 schema、可读的配置数据、以及执行日志能力。在当前项目规模下，这个成本是合理的。

### [Trade-off] 超时阈值的粒度
**→ 接受**：10 分钟对于进程崩溃场景足够快，但对于网络抖动导致的短暂卡顿可能过于激进。通过配置化（`SYNC_TASK_STALE_TIMEOUT_MINUTES`）允许用户调整。
