# 交付与可观测性文档 - Stock Helper

## 1) 测试体系

### 测试分层结构

```
tests/
├── unit/                          # 单元测试
│   ├── modules/
│   │   ├── data_engineering/      # 数据工程模块测试
│   │   │   ├── application/
│   │   │   │   └── services/      # Service 层测试
│   │   │   └── commands/          # Command 层测试
│   │   └── foundation/            # 基础设施模块测试
│   └── shared/                    # 共享模块测试
│
├── integration/                   # 集成测试
│   ├── modules/                   # 模块间集成测试
│   └── shared/                    # 共享基础设施集成测试
│
└── e2e/                           # 端到端测试
    └── api/                       # API 层 E2E 测试
```

### 测试框架与工具

| 工具 | 用途 | 配置位置 |
|------|------|----------|
| **pytest** | 测试运行器 | `pytest.ini`, `pyproject.toml` |
| **pytest-asyncio** | 异步测试支持 | `pytest.ini: --asyncio-mode=auto` |
| **pytest-cov** | 覆盖率报告 | `pyproject.toml: [tool.coverage]` |
| **httpx** | API 测试客户端 | `requirements.txt` |
| **TestContainers** | 容器化测试依赖 | 未引入（建议添加） |

### 测试覆盖范围

**已覆盖**:
- Service 层业务逻辑（`test_*_service.py`）
- Command 层命令执行（`test_sync_*_cmd.py`）
- DTO/类型定义（`test_*_dtos.py`）
- 异常处理（`test_*_exceptions.py`）

**缺失**:
- API 层集成测试（MockMvc 风格）
- 数据库持久化测试（真实 DB）
- 外部 API 集成测试（Tushare/LLM）
- E2E 流程测试

### 测试示例

**单元测试** (`tests/unit/modules/foundation/test_scheduler_application_service.py`):
```python
@pytest.mark.asyncio
async def test_start_scheduler():
    # Arrange
    mock_scheduler_port = AsyncMock()
    service = SchedulerApplicationService(mock_scheduler_port, ...)

    # Act
    await service.start_scheduler()

    # Assert
    mock_scheduler_port.start_scheduler.assert_called_once()
```

**覆盖率要求**（`pyproject.toml:45-59`）:
```toml
[tool.coverage.run]
source = ["src"]
omit = [
    "*/tests/*",
    "*/test_*",
    "*/__pycache__/*",
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
]
```

---

## 2) CI/CD 流水线

### GitHub Actions CI (`ci.yml`)

**触发条件**:
- Push 到 `main` 分支
- Pull Request 到 `main` 分支

**流水线步骤**:

```yaml
1. Checkout 代码
   ↓
2. 设置 Python 3.10 环境
   ↓
3. 安装依赖 (pip install -r requirements.txt)
   ↓
4. 代码质量检查
   ├── flake8 src tests (代码规范)
   └── mypy (类型检查，当前禁用)
   ↓
5. 运行测试
   ├── 启动 PostgreSQL 15 容器
   ├── 设置测试环境变量
   └── pytest tests/ (当前跳过)
```

**服务依赖**:
- PostgreSQL 15 (TestContainers 风格)
  - 数据库：`stock_helper_test`
  - 健康检查：`pg_isready`

**当前问题**:
- 测试被注释掉（`# pytest tests/`）
- MyPy 类型检查被禁用
- 无 Neo4j 测试容器

### 建议的 CD 流水线（未实现）

```yaml
部署到生产环境:
  触发条件：Release Tag (v*)
  步骤:
    1. 构建 Docker 镜像
    2. 推送到 ECR/ Docker Hub
    3. 更新 Kubernetes Deployment / ECS Task
    4. 运行数据库迁移 (alembic upgrade head)
    5. 健康检查
    6. 回滚（若健康检查失败）
```

---

## 3) 可观测性

### 日志框架

**技术栈**: Loguru + Structlog

**配置**: `src/shared/infrastructure/logging.py`

**日志格式**:
```
# 开发环境
2024-01-15 10:30:45.123 | DEBUG    | Thread-140234 | src.main:lifespan:28 - Application starting up...

# 生产环境 (JSON 序列化)
{"timestamp": "2024-01-15T10:30:45.123Z", "level": "DEBUG", "thread": 140234, "name": "src.main", "function": "lifespan", "line": 28, "message": "Application starting up..."}
```

**日志级别分布**:
- `DEBUG`: 详细调试信息（开发环境）
- `INFO`: 正常业务流程（启动/关闭/任务完成）
- `WARNING`: 可恢复的异常（如 API 限流等待）
- `ERROR`: 需要关注的错误（同步失败）
- `EXCEPTION`: 未捕获异常（带堆栈）

### TraceId/链路追踪

**当前状态**: 未实现分布式追踪

**建议方案**:
1. **OpenTelemetry**: 添加 traceparent header 传递
2. **日志关联 ID**: 每请求生成 `request_id`
3. **结构化日志**: 所有日志包含 `request_id` 字段

```python
# 中间件添加 request_id
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response

# 日志中携带
logger.bind(request_id=request.state.request_id).info("Processing request")
```

### Metrics/Prometheus

**当前状态**: 已安装 `prometheus-client`（`requirements.txt:11`），但未见集成

**建议 Metrics**:
```python
from prometheus_client import Counter, Histogram

# 请求计数器
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

# 请求延迟直方图
REQUEST_LATENCY = Histogram(
    'http_request_latency_seconds',
    'HTTP request latency',
    ['method', 'endpoint'],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0]
)

# 外部 API 调用
EXTERNAL_API_CALLS = Counter(
    'external_api_calls_total',
    'External API calls',
    ['provider', 'endpoint', 'status']
)
```

### Health Check

**端点**: `GET /api/v1/health`

**实现**: `src/api/health.py`

**检查项**:
- 数据库连接（`SELECT 1`）
- 应用状态

**Docker 健康检查** (`docker-compose.yml:25-30`):
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 15s
```

### 异常/慢请求定位

**当前能力**:
- 异常日志记录（`ErrorHandlingMiddleware`）
- 错误堆栈输出

**改进建议**:
1. **慢查询日志**: SQLAlchemy `echo=True` + 阈值告警
2. **请求日志**: 记录每个请求的开始/结束时间
3. **性能剖析**: 集成 `py-spy` 或 `austin`

```python
# 慢请求中间件
@app.middleware("http")
async def log_slow_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration_ms = (time.time() - start) * 1000

    if duration_ms > 1000:  # > 1s
        logger.warning(
            f"Slow request: {request.method} {request.url.path} took {duration_ms:.2f}ms"
        )
    return response
```

---

## 4) 线上故障故事模板

### 故障故事 1: 定时任务泄露导致内存OOM

**发现**:
```
# Prometheus 告警
Alert: ContainerMemoryUsageHigh
Stock_Helper_App container memory usage > 90% for 5m
```

**定位**:
```bash
# 1. 查看容器日志
docker compose logs app | grep -i "memory\|error"

# 2. 检查 Python 进程
docker compose exec app ps aux | grep python

# 3. 使用 py-spy 分析（若已安装）
py-spy dump --pid <PID>
```

**日志线索**:
```
2024-01-15 03:00:00.123 | INFO | Scheduler executing job: sync_daily_bars
2024-01-15 03:00:01.456 | WARNING | Memory usage high: 1.2GB / 512MB limit
2024-01-15 03:00:05.789 | ERROR | Job sync_daily_bars failed: MemoryError
```

**根因**:
- 定时任务 `sync_daily_bars` 未正确释放数据库连接
- 多次失败后重试累积，连接池耗尽
- 容器内存超限被 OOMKilled

**修复**:
1. 添加连接池大小限制（`pool_size=10`）
2. 任务执行后显式关闭 session
3. 添加背压控制（队列限制）

**代码变更**:
```python
# src/modules/data_engineering/application/commands/sync_daily_history_cmd.py
async def execute(self, limit=10, offset=0):
    async with self._db_session() as session:  # 使用上下文管理器
        # ... 处理逻辑
    # session 自动关闭
```

**复盘改进**:
- 添加内存使用率告警（>70% 预警）
- 定时任务添加超时（`timeout=300s`）
- 添加连接池监控 metrics

---

### 故障故事 2: LLM API 变更导致技术分析全挂

**发现**:
```
# 用户报告
"技术分析接口返回 422，所有股票分析失败"

# Grafana 面板
external_api_calls_total{provider="bocha", status="error"} 飙升
```

**定位**:
```bash
# 查看错误日志
docker compose logs app | grep "LLM\|parse\|422"

# 错误堆栈
src/modules/research/infrastructure/adapters/technical_analyst_agent_adapter.py:45
LLMOutputParseError: Failed to parse LLM output: Expected field 'signal' not found
```

**根因**:
- Bocha AI 模型升级，输出格式从 `{"signal": "BULLISH"}` 改为 `{"analysis_result": {"signal": "BULLISH"}}`
- 输出解析器未适配新格式

**修复**:
1. 紧急：回滚到旧模型版本
2. 长期：添加输出格式版本检测，自动适配

**代码变更**:
```python
# src/modules/research/infrastructure/agents/technical_analyst/output_parser.py
def parse_llm_output(raw_output: str) -> TechnicalAnalysisResult:
    data = json.loads(raw_output)

    # 兼容新旧格式
    if "analysis_result" in data:
        data = data["analysis_result"]

    return TechnicalAnalysisResult(
        signal=data["signal"],
        confidence=data["confidence"],
        ...
    )
```

**复盘改进**:
- 添加 LLM 输出格式监控（Schema 验证）
- 输出解析失败时保留原始响应便于调试
- 与 LLM 提供商建立变更通知机制

---

### 故障故事 3: 数据库迁移失败导致服务启动失败

**发现**:
```
# Docker 健康检查失败
stock_helper_app unhealthy

# 日志
alembic.util.exc.CommandError: Target database is not up to date
```

**定位**:
```bash
# 检查迁移状态
docker compose exec app alembic current
# 输出：(empty) - 迁移表不存在

docker compose exec app alembic history
# 输出：显示多个待应用迁移
```

**根因**:
- 新部署时 `alembic upgrade head` 因表冲突失败
- 部分迁移已应用，但标记未完成
- 应用启动检查迁移状态，发现不一致拒绝启动

**修复**:
```bash
# 手动修复迁移标记
docker compose exec app alembic stamp head
docker compose exec app alembic upgrade head
```

**复盘改进**:
- 迁移脚本添加幂等检查
- 启动流程改为：先迁移 → 健康检查 → 注册到负载均衡
- 添加迁移失败告警

---

## 面试口述版故障故事

> "上线后第二天早上 9 点，收到 Prometheus 告警，说容器内存使用率超过 90%。我第一反应是看 Grafana 面板，发现是定时任务 `sync_daily_bars` 在凌晨 3 点执行时内存飙升。
>
> 查看日志发现任务执行了 5 分钟还没结束，内存从 200MB 一路涨到 1.2GB（容器限制 512MB）。进一步分析代码，发现问题是同步日线数据时一次性加载了全量股票到内存，没有分页。
>
> 修复方案是分三步：
> 1. 紧急上线：先把这个定时任务禁用，避免继续 OOM
> 2. 代码修复：添加分页逻辑，每次处理 10 只股票，处理完释放内存
> 3. 长期优化：引入背压控制，用异步队列限制生产者速度
>
> 复盘后我们加了三个监控：
> - 内存使用率超过 70% 就告警（别等到 90%）
> - 定时任务执行时间超过 5 分钟告警
> - 数据库连接池使用率监控
>
> 这次故障让我深刻体会到，批处理任务一定要有限流和背压机制，不然生产环境的数据量很容易把开发时的假设打破。"
