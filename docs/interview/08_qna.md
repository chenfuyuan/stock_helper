# 高频面试 Q&A 题库 - Stock Helper

## 架构设计（8 题）

### Q1: 为什么选择模块化单体而不是微服务？

**标准回答**：
模块化单体是在开发效率、运维复杂度和未来扩展性之间的权衡。微服务适合大团队和多语言场景，但引入分布式事务、服务发现问题。

**结合本项目**：
- 团队规模：目前 1 个开发，微服务运维成本过高
- 数据一致性：共享 PostgreSQL，避免分布式事务
- 模块边界：每个模块内部 DDD 分层，通过 Container 依赖注入解耦
- 未来拆分：模块可独立打包，通过 gRPC 通信

**证据**：`src/modules/*/`, `src/api/routes.py`（统一路由注册）

**可能追问**：那你怎么保证模块间不产生循环依赖？
- 答：通过依赖倒置（Domain 层定义 Port），模块只能依赖 Domain 层接口，不能直接跨模块调用 Infrastructure

---

### Q2: 你们的 DDD 分层具体是怎么做的？

**标准回答**：
DDD 分层包括 Domain（领域模型）、Application（应用服务）、Infrastructure（基础设施）、Presentation（接口）。

**结合本项目**：
```
modules/research/
├── domain/
│   ├── entities/        # 领域实体（如 TechnicalAnalysisResult）
│   ├── ports/           # 仓储/服务接口（如 IMarketQuotePort）
│   └── exceptions/      # 领域异常（如 LLMOutputParseError）
├── application/
│   └── technical_analyst_service.py  # 应用服务（编排用例）
├── infrastructure/
│   ├── adapters/        # 外部 API 适配器
│   ├── persistence/     # 数据库仓储实现
│   └── agents/          # Agent 实现层
└── presentation/
    └── rest/            # FastAPI Router
```

**依赖方向**：Infrastructure → Domain ← Application ← Presentation

**证据**：`src/modules/research/` 目录结构

---

### Q3: 什么是依赖倒置？你们怎么用？

**标准回答**：
依赖倒置（DIP）指高层模块不依赖低层模块，二者都依赖抽象。抽象不应依赖细节，细节应依赖抽象。

**结合本项目**：
- Domain 层定义 Port 接口（如 `IMarketQuotePort.get_daily_bars()`）
- Infrastructure 层实现 Port（如 `MarketQuoteAdapter` 调用 Tushare API）
- Application 层只依赖 Port，不关心具体实现

```python
# Domain 层定义
class IMarketQuotePort(Protocol):
    async def get_daily_bars(self, ticker: str, start_date: date) -> List[DailyBar]:
        ...

# Application 层使用
class TechnicalAnalystService:
    def __init__(self, market_quote_port: IMarketQuotePort):
        self._market_quote = market_quote_port  # 只依赖接口

# Infrastructure 层实现
class MarketQuoteAdapter(IMarketQuotePort):
    async def get_daily_bars(self, ticker, start_date):
        return await self._tushare_client.fetch_daily(ticker, start_date)
```

**证据**：`src/modules/research/domain/ports/`, `src/modules/research/infrastructure/adapters/`

---

### Q4: 你们的服务怎么发现？依赖注入怎么做？

**标准回答**：
使用 Composition Root 模式，每个模块有 Container 类负责组装依赖。

**结合本项目**：
```python
# src/modules/research/container.py
class ResearchContainer:
    def __init__(self, db: AsyncSession):
        self.db = db

    def technical_analyst_service(self) -> TechnicalAnalystService:
        return TechnicalAnalystService(
            market_quote_port=self.market_quote_adapter(),
            indicator_calculator=self.indicator_calculator(),
            analyst_agent_port=self.technical_analyst_agent_adapter(),
        )

    def market_quote_adapter(self) -> IMarketQuotePort:
        return MarketQuoteAdapter(self.db)
```

路由层通过 Depends 获取：
```python
async def get_service(db: AsyncSession = Depends(get_db_session)):
    return ResearchContainer(db).technical_analyst_service()
```

**证据**：`src/modules/*/container.py`

---

### Q5: 你们有考虑过 CQRS 吗？

**标准回答**：
CQRS 分离读写操作，适合读写负载不均衡场景（如读多写少）。

**结合本项目**：
- 当前状态：未严格实现 CQRS，但 Command 和 Query DTO 已分离
- 适用场景：技术分析（读）vs 数据同步（写）负载不同
- 未来改进：可用不同数据库优化（读：Neo4j，写：PostgreSQL）

**证据**：`src/modules/data_engineering/application/commands/` vs `src/modules/data_engineering/application/queries/`

---

### Q6: 异步编程的优缺点？遇到过什么问题？

**标准回答**：
- 优点：高并发下资源利用率高，IO 阻塞不占用线程
- 缺点：调试困难、堆栈深、CPU 密集型任务需卸载

**踩坑**：
- Pandas 指标计算是同步的，会阻塞事件循环
- 解法：`run_in_executor` 放到线程池

```python
async def compute(self, bars):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, self._compute_sync, bars)
```

**证据**：需检查 `src/modules/research/infrastructure/indicators/`

---

### Q7: 你们的异常怎么处理？有全局异常处理吗？

**标准回答**：
使用 FastAPI 中间件统一捕获异常，返回统一格式。

**结合本项目**：
```python
# src/api/middlewares/error_handler.py
class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        try:
            return await call_next(request)
        except AppException as e:
            return JSONResponse(status_code=e.status_code, content=ErrorResponse(...))
        except Exception as e:
            logger.exception(f"未捕获异常：{e}")
            return JSONResponse(status_code=500, content=ErrorResponse(...))
```

**证据**：`src/api/middlewares/error_handler.py`

---

### Q8: 如果让你们系统支持多租户，怎么改？

**标准回答**：
- 数据库层：添加 `tenant_id` 字段，所有查询加过滤
- 服务层：从 JWT Token 提取 tenant_id
- 隔离级别：数据库行级隔离 or 独立 Schema

**结合本项目**：
```python
# 在 BaseRepository 中添加租户过滤
class BaseRepository:
    async def find_by_ticker(self, ticker: str, tenant_id: str):
        return await self.db.execute(
            select(Stock).where(
                Stock.ticker == ticker,
                Stock.tenant_id == tenant_id
            )
        )
```

---

## 事务与一致性（5 题）

### Q9: 你们怎么保证数据同步的事务性？

**标准回答**：
每只股票的日线数据写入在同一事务内，使用数据库唯一约束保证幂等。

**结合本项目**：
```python
# PostgreSQL upsert
INSERT INTO stock_daily_bars (ticker, date, open, high, low, close)
VALUES (...)
ON CONFLICT (ticker, date) DO UPDATE SET
    open = EXCLUDED.open,
    close = EXCLUDED.close
```

**证据**：`src/modules/data_engineering/infrastructure/persistence/repositories/pg_quote_repo.py`

---

### Q10: 分布式事务怎么处理？（如 Neo4j 和 PG 双写）

**标准回答**：
当前未使用分布式事务，通过最终一致性保证：
1. 先写 PostgreSQL（主数据）
2. 异步同步到 Neo4j（通过定时任务）
3. 失败重试机制

**改进方案**：
- 事件驱动：PG 写入后发布事件，Neo4j 订阅消费
- Saga 模式：Neo4j 失败时触发补偿事务（删除 PG 标记）

---

### Q11: 你们的幂等性怎么保证？

**标准回答**：
- 数据库层：唯一约束（ticker + date）
- 业务层：任务状态表记录已处理的股票
- API 层：请求 ID 去重（未实现）

**结合本项目**：
```python
# SyncTask 表记录同步进度
class SyncTask(Base):
    task_id: str
    ticker: str
    status: str  # pending/running/success/failed
    retry_count: int
```

**证据**：`src/modules/data_engineering/domain/ports/repositories/sync_task_repo.py`

---

### Q12: 如果定时任务重复执行了怎么办？

**标准回答**：
- 数据库锁：`SELECT ... FOR UPDATE SKIP LOCKED`
- 分布式锁：Redis `SETNX`（未实现）
- 任务状态表：检查是否有正在运行的同类型任务

**结合本项目**：
```python
async def execute(self):
    # 检查是否有正在运行的任务
    running = await self._repo.find_running_task(job_type="sync_daily")
    if running:
        logger.warning(f"任务已在运行：{running.task_id}")
        return
```

---

### Q13: 重试机制怎么做？有考虑过重试风暴吗？

**标准回答**：
- 指数退离：`wait_exponential(min=1, max=60)`
- 最大重试次数：`stop_after_attempt(3)`
- 重试风暴预防：添加 jitter 随机延迟

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=60))
async def sync_with_retry():
    ...
```

---

## 并发与性能（6 题）

### Q14: 你们系统 QPS 多少？瓶颈在哪里？

**标准回答**：
- 未压测，估算 QPS ~50（单实例）
- 瓶颈：LLM 调用（3-10s 响应）
- 改进：缓存分析结果（1 小时过期）

---

### Q15: 数据库连接池怎么配置？

**标准回答**：
```python
create_async_engine(
    ...,
    pool_size=20,          # 基础连接数
    max_overflow=40,       # 最大连接数 = 60
    pool_pre_ping=True,    # 自动检测失效连接
    pool_recycle=3600,     # 1 小时回收
)
```

---

### Q16: 有遇到过 N+1 查询吗？怎么解决？

**标准回答**：
- 问题：图谱同步时，每只股票单独查询行业节点
- 解决：预加载所有行业到内存，使用 Map 查找

```python
# 预加载
industries = await graph.run("MATCH (i:Industry) RETURN i.code, i")
industry_map = {r['i']['code']: r['i'] for r in industries}

# 使用 Map，避免 N 次查询
for stock in stocks:
    industry = industry_map.get(stock.industry_code)
```

---

### Q17: 批量处理怎么优化？

**标准回答**：
- 分页：每次处理 10-100 条
- 背压：异步队列限制 `maxsize=100`
- 批量写入：Neo4j `UNWIND` 代替单条插入

---

### Q18: 缓存层怎么设计？

**标准回答**：
```python
async def get_technical_analysis(ticker, date):
    cache_key = f"tech:{ticker}:{date}"
    cached = await redis.get(cache_key)
    if cached:
        return json.loads(cached)

    result = await self._analyze(ticker, date)
    await redis.setex(cache_key, 3600, json.dumps(result))
    return result
```

---

### Q19: 异步队列用过吗？怎么实现的？

**标准回答**：
```python
from asyncio import Queue

queue = Queue(maxsize=100)  # 背压：队列满时阻塞

async def producer():
    for stock in stocks:
        await queue.put(stock)

async def consumer():
    while True:
        stock = await queue.get()
        await process(stock)
        queue.task_done()
```

---

## 数据库（5 题）

### Q20: PostgreSQL 索引怎么设计？

**标准回答**：
```sql
-- 日线表
CREATE INDEX idx_daily_ticker_date ON stock_daily_bars(ticker, date DESC);
-- 股票表
CREATE INDEX idx_stocks_industry ON stocks(industry_code);
```

---

### Q21: 有遇到过慢查询吗？怎么排查？

**标准回答**：
- 开启慢查询日志：`log_min_duration_statement = 1000`
- 使用 `EXPLAIN ANALYZE` 分析执行计划
- 添加缺失索引

---

### Q22: Alembic 迁移怎么管理？

**标准回答**：
```bash
# 创建迁移
alembic revision --autogenerate -m "add_stock_table"

# 应用迁移
alembic upgrade head

# 回滚
alembic downgrade -1
```

**证据**：`alembic/versions/`

---

### Q23: Neo4j 和 PostgreSQL 数据一致性怎么保证？

**标准回答**：
- 当前：异步同步（定时任务）
- 改进：事件驱动（PG 写入后发布事件，Neo4j 订阅）

---

### Q24: 数据库分库分表考虑过吗？

**标准回答**：
- 当前数据量：日线表 ~500 万行，无需分表
- 未来方案：按 ticker 哈希分表（`daily_bars_00` ~ `daily_bars_99`）

---

## 缓存（3 题）

### Q25: 缓存穿透怎么解决？

**标准回答**：
- 布隆过滤器：检查 ticker 是否存在
- 缓存空值：不存在的 ticker 也缓存（5 分钟过期）

---

### Q26: 缓存雪崩怎么解决？

**标准回答**：
- 随机过期时间：`3600 + random(0, 600)`
- 热点数据永不过期：后台定时刷新

---

### Q27: 缓存击穿怎么解决？

**标准回答**：
- 互斥锁：`redis.set(lock_key, "1", nx=True, ex=10)`
- 逻辑过期：后台线程刷新，用户读到旧数据

---

## 消息队列（3 题）

### Q28: 有用过消息队列吗？

**标准回答**：
- 当前：APScheduler 内存队列
- 未来：RabbitMQ/Celery 异步任务

---

### Q29: 消息丢失怎么处理？

**标准回答**：
- 持久化：队列/消息都持久化到磁盘
- 确认机制：消费者 ACK 后删除

---

### Q30: 消息堆积怎么处理？

**标准回答**：
- 监控：队列长度告警
- 扩容：增加消费者
- 降级：丢弃低优先级消息

---

## 异常与稳定性（4 题）

### Q31: 线上服务挂了怎么发现？

**标准回答**：
- 健康检查：每 30s `GET /api/v1/health`
- Prometheus 监控：QPS/延迟/错误率
- 日志告警：ERROR 日志超过阈值

**证据**：`docker-compose.yml:25-30`（健康检查）

---

### Q32: 怎么做限流？

**标准回答**：
```python
# 滑动窗口限流
class SlidingWindowRateLimiter:
    async def acquire(self):
        now = time.monotonic()
        # 清理窗口外时间戳
        while self._timestamps and now - self._timestamps[0] >= self._window:
            self._timestamps.popleft()

        # 达到上限则等待
        if len(self._timestamps) >= self._max_calls:
            wait_time = self._window - (now - self._timestamps[0])
            await asyncio.sleep(wait_time)

        self._timestamps.append(now)
```

**证据**：`src/modules/data_engineering/infrastructure/external_apis/tushare/rate_limiter.py`

---

### Q33: 怎么做降级？

**标准回答**：
- LLM 超时：返回缓存结果 or 简化版分析
- Tushare 限流：切换到 Akshare

---

### Q34: 怎么做熔断？

**标准回答**：
```python
from circuitbreaker import circuit

@circuit(failure_threshold=5, recovery_timeout=30)
async def call_tushare_api():
    ...
```

---

## 安全（3 题）

### Q35: 怎么防止 SQL 注入？

**标准回答**：
- 参数化查询：`await db.execute(text("SELECT * FROM stocks WHERE ticker = :ticker"), {"ticker": ticker})`
- ORM：SQLAlchemy 自动参数化

---

### Q36: 敏感信息怎么存储？

**标准回答**：
- 当前：.env 文件（开发环境）
- 生产：云厂商 Secrets Manager / Kubernetes Secrets
- 加密：密码使用 bcrypt 哈希

---

### Q37: 怎么做认证授权？

**标准回答**：
```python
from fastapi.security import HTTPBearer

security = HTTPBearer()

async def get_current_user(creds: HTTPAuthorizationCredentials = Depends(security)):
    token = creds.credentials
    user = await verify_jwt(token)
    if not user:
        raise HTTPException(status_code=401)
    return user
```

---

## 测试（3 题）

### Q38: 单元测试覆盖率多少？

**标准回答**：
- 当前：估计 ~40%（主要集中在 Service 层）
- 目标：核心业务逻辑 >80%

**证据**：`tests/unit/`

---

### Q39: 怎么做集成测试？

**标准回答**：
```python
@pytest.mark.asyncio
async def test_technical_analysis_api():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/v1/research/technical-analysis?ticker=000001.SZ")
        assert response.status_code == 200
```

---

### Q40: 怎么做 Mock 测试？

**标准回答**：
```python
from unittest.mock import AsyncMock

async def test_service_with_mock():
    mock_market_quote = AsyncMock()
    mock_market_quote.get_daily_bars.return_value = [DailyBar(...)]

    service = TechnicalAnalystService(mock_market_quote, ...)
    result = await service.run("000001.SZ", date.today())

    mock_market_quote.get_daily_bars.assert_called_once()
```

---

## 上线与排障（3 题）

### Q41: 怎么做灰度发布？

**标准回答**：
- Nginx 权重：10% 流量到新服务
- Kubernetes：Canary Deployment
- 功能开关：配置中心动态切换

---

### Q42: 线上 CPU 飙高怎么排查？

**标准回答**：
```bash
# 1. 找到占用 CPU 的进程
top -H -p <PID>

# 2. 使用 py-spy 分析
py-spy top --pid <PID>

# 3. 查看线程堆栈
py-spy dump --pid <PID>
```

---

### Q43: 内存泄露怎么排查？

**标准回答**：
```bash
# 1. 查看内存使用
docker stats

# 2. 使用 memory_profiler
from memory_profiler import profile

@profile
def my_func():
    ...

# 3. 分析对象引用
import objgraph
objgraph.show_growth()
```

---

## 附加题（开放性问题）

### Q44: 如果让你重新设计这个系统，你会做什么不同的选择？

**回答要点**：
- 引入 Redis 缓存层（减少 LLM 调用）
- 使用事件驱动架构（PG → Neo4j 异步同步）
- 添加 API 认证（JWT + 配额管理）
- 完善监控告警（Prometheus + Grafana）

---

### Q45: 你们系统的技术债务有哪些？

**回答要点**：
- 测试覆盖率不足（~40%）
- 无缓存层（重复调用 LLM）
- 无分布式追踪（TraceID）
- 部分代码未异步化（阻塞事件循环）
