# 模拟面试脚本 - Stock Helper

## 面试流程概览

```
1. 项目介绍（5 分钟）
   └─ 2 分钟电梯演讲 + 3 分钟追问

2. 架构深入（10 分钟）
   └─ DDD 分层、模块化、依赖注入

3. 核心链路（10 分钟）
   └─ 技术分析流程、图谱同步

4. 性能与并发（10 分钟）
   └─ 异步编程、缓存、限流

5. 事务与一致性（5 分钟）
   └─ 幂等性、重试、分布式事务

6. 安全与稳定性（5 分钟）
   └─ 认证、限流、熔断

7. 测试与排障（5 分钟）
   └─ 单元测试、线上故障排查

8. 系统设计（10 分钟）
   └─ 扩展题：如何支持多租户/高并发
```

---

## 30-40 个递进式问题

### 第一部分：项目介绍（1-5 题）

#### Q1: 请简单介绍一下你的项目

**考察点**：沟通能力、项目理解深度

**优秀回答结构**：
1. 一句话定位（业务目标 + 目标用户）
2. 核心功能（2-3 个亮点）
3. 技术栈（框架 + 关键组件）
4. 架构特点（模块化/分布式/...）
5. 个人贡献（我负责...）

**示例回答**：
> 这是一个 A 股智能研究分析平台，目标是用 AI 自动化替代人工完成股票研究。
>
> 核心功能有三个：
> 1. 技术分析 Agent：输入股票代码，输出买卖信号和置信度
> 2. 财务审计 Agent：AI 分析财报，识别潜在风险
> 3. 知识图谱：基于 Neo4j 的股票 - 概念关系网络
>
> 技术栈上，后端用 FastAPI + SQLAlchemy Async，数据源接 Tushare/Akshare，AI 用 LangGraph 多 Agent 框架。
>
> 架构是模块化单体，每个模块内部 DDD 分层，通过依赖注入解耦。
>
> 我个人负责了整体架构设计、核心模块开发（Research/Knowledge Center），以及数据工程 pipeline 搭建。

**常见扣分点**：
- 只说技术，不说业务价值
- 功能罗列，没有重点
- 说不清个人贡献

---

#### Q2: 为什么选择 FastAPI 而不是 Flask/Django？

**考察点**：技术选型能力、框架理解

**优秀回答**：
- **异步支持**：FastAPI 原生 async/await，高并发下性能更好
- **自动文档**：Swagger UI 自动生成，前端对接方便
- **类型推导**：Pydantic 模型自动验证，减少 boilerplate
- **学习曲线**：比 Django 轻量，比 Flask 结构化

**结合项目**：
> 我们 IO 密集型场景（DB/LLM API 调用）多，异步能充分利用 CPU。
> 实测单实例 QPS ~50，比 Flask 高 2-3 倍。

**常见扣分点**：
- 只说「FastAPI 快」，说不清为什么快
- 不知道异步和同步的本质区别

---

#### Q3: 你们的数据从哪来？怎么保证时效性？

**考察点**：数据源理解、数据质量控制

**优秀回答**：
- **数据源**：Tushare（付费，稳定）+ Akshare（开源，补充）
- **同步策略**：
  - 日线数据：每日收盘后自动同步（定时任务）
  - 财务数据：财报发布后增量同步
  - 概念数据：每周全量刷新
- **时效性**：T+1（日线延迟 1 天）

**证据**：`src/modules/data_engineering/application/services/daily_sync_service.py`

---

#### Q4: 多 Agent 是怎么协作的？

**考察点**：Agent 架构理解、LangGraph 使用

**优秀回答**：
```
用户请求
    ↓
Coordinator（编排器）
    ├─→ 技术分析 Agent → 技术面观点
    ├─→ 财务审计 Agent → 基本面观点
    └─→ 估值建模 Agent → 合理估值区间
    ↓
Debate（辩论）→ Judge（决策）
    ↓
最终投资建议
```

**结合项目**：
> 目前实现的是「并行分析 + 汇总」模式，每个 Agent 独立工作。
> 下一步计划实现真正的辩论：看涨 Agent 和看跌 Agent 互相反驳，Judge 综合双方论据。

**证据**：`src/modules/coordinator/application/research_orchestration_service.py`

---

#### Q5: Agent 的输出怎么保证格式正确？

**考察点**：LLM 输出解析、容错处理

**优秀回答**：
1. **Prompt 设计**：明确要求输出 JSON 格式
2. **Schema 验证**：Pydantic 模型解析
3. **重试机制**：解析失败自动重试（最多 3 次）
4. **降级策略**：多次失败后返回「分析失败」

```python
# src/modules/research/infrastructure/agents/technical_analyst/output_parser.py
def parse_llm_output(raw: str) -> TechnicalAnalysisResult:
    try:
        data = json.loads(raw)
        return TechnicalAnalysisResult(**data)  # Pydantic 验证
    except (json.JSONDecodeError, ValidationError) as e:
        raise LLMOutputParseError(f"解析失败：{e}")
```

---

### 第二部分：架构深入（6-12 题）

#### Q6: 你们说的 DDD 分层，每层具体做什么？

**考察点**：DDD 理解深度

**优秀回答**：
| 层 | 职责 | 典型文件 |
|----|------|----------|
| Domain | 领域模型、业务规则、Port 接口 | `entities/`, `ports/`, `exceptions/` |
| Application | 用例编排、事务管理 | `*_service.py` |
| Infrastructure | 外部依赖适配、持久化 | `adapters/`, `persistence/` |
| Presentation | HTTP 接口、参数验证 | `rest/*.py` |

**依赖规则**：Infrastructure → Domain ← Application ← Presentation

---

#### Q7: 什么是依赖倒置？你们怎么用？

**考察点**：SOLID 原则理解

**优秀回答**：
> 依赖倒置指高层模块不依赖低层模块，二者都依赖抽象。
>
> 我们的做法：
> - Domain 层定义 Port 接口（如 `IMarketQuotePort`）
> - Application 层依赖 Port（构造函数注入）
> - Infrastructure 层实现 Port（如 `MarketQuoteAdapter`）

```python
# Domain 层
class IMarketQuotePort(Protocol):
    async def get_daily_bars(self, ticker: str) -> List[DailyBar]: ...

# Application 层
class TechnicalAnalystService:
    def __init__(self, market_quote: IMarketQuotePort): ...

# Infrastructure 层
class MarketQuoteAdapter(IMarketQuotePort):
    async def get_daily_bars(self, ticker: str): ...
```

---

#### Q8: 模块间怎么解耦？有循环依赖吗？

**考察点**：模块化设计能力

**优秀回答**：
- **解耦方式**：Container 依赖注入，模块间不直接 import
- **循环依赖检查**：暂未发现（Domain 层无依赖）
- **边界**：通过 `src/api/routes.py` 统一注册路由

**证据**：`src/modules/*/container.py`

---

#### Q9: 如果让你们系统支持高并发，怎么改？

**考察点**：扩展性思考

**优秀回答**：
1. **缓存层**：Redis 缓存技术分析结果（1 小时过期）
2. **读写分离**：PostgreSQL 主从复制
3. **水平扩展**：Kubernetes HPA 自动扩容
4. **异步任务**：Celery + RabbitMQ 卸载耗时操作
5. **CDN**：静态资源上 CDN

---

#### Q10: 你们怎么做依赖注入？有用什么框架吗？

**考察点**：DI 模式理解

**优秀回答**：
- **框架**：Dependency-Injector（`requirements.txt:19`）
- **模式**：Composition Root（每个模块 Container 类）
- **生命周期**：Singleton（服务）vs Transient（每次请求新建）

```python
# src/modules/research/container.py
class ResearchContainer:
    def technical_analyst_service(self) -> TechnicalAnalystService:
        return TechnicalAnalystService(
            market_quote_port=self.market_quote_adapter(),
            indicator_calculator=self.indicator_calculator(),
            ...
        )
```

---

#### Q11: 你们的配置怎么管理？多环境怎么切换？

**考察点**：配置管理实践

**优秀回答**：
- **配置类**：Pydantic Settings（`src/shared/config.py`）
- **加载顺序**：环境变量 > .env 文件 > 默认值
- **多环境**：`ENVIRONMENT` 变量区分（local/dev/prod）

```python
class Settings(BaseSettings):
    ENVIRONMENT: str = "local"
    POSTGRES_SERVER: str = "localhost"

    class Config:
        env_file = ".env"
        extra = "ignore"  # 忽略多余字段
```

---

#### Q12: 数据库迁移怎么做的？

**考察点**：数据库版本管理

**优秀回答**：
- **工具**：Alembic（SQLAlchemy 官方迁移工具）
- **流程**：
  ```bash
  alembic revision --autogenerate -m "add_stock_table"
  alembic upgrade head
  ```
- **回滚**：`alembic downgrade -1`

**证据**：`alembic/versions/`

---

### 第三部分：核心链路（13-18 题）

#### Q13: 技术分析接口的完整调用链是什么？

**考察点**：系统理解深度

**优秀回答**：
```
GET /api/v1/research/technical-analysis?ticker=000001.SZ
    ↓
TechnicalAnalystRoutes.run_technical_analysis()
    ↓
TechnicalAnalystService.run(ticker, date)
    ├─→ IMarketQuotePort.get_daily_bars()  # 读取日线
    ├─→ IIndicatorCalculator.compute()     # 计算指标
    └─→ ITechnicalAnalystAgentPort.analyze() # LLM 分析
    ↓
BaseResponse[TechnicalAnalysisApiResponse]
```

**文件路径**：
- Controller: `src/modules/research/presentation/rest/technical_analyst_routes.py:51`
- Service: `src/modules/research/application/technical_analyst_service.py:38`

---

#### Q14: 技术指标怎么计算的？有哪些指标？

**考察点**：领域知识

**优秀回答**：
```python
# src/modules/research/infrastructure/indicators/calculator.py
def compute(self, bars: List[DailyBar]) -> TechnicalIndicatorSnapshot:
    df = pd.DataFrame([b.model_dump() for b in bars])

    # MA
    df['ma5'] = df['close'].rolling(5).mean()
    df['ma20'] = df['close'].rolling(20).mean()

    # MACD(12, 26, 9)
    ema12 = df['close'].ewm(span=12).mean()
    ema26 = df['close'].ewm(span=26).mean()
    df['macd_dif'] = ema12 - ema26
    df['macd_dea'] = df['macd_dif'].ewm(span=9).mean()

    # 布林带 (20, 2)
    df['bb_middle'] = df['close'].rolling(20).mean()
    df['bb_std'] = df['close'].rolling(20).std()
    df['bb_upper'] = df['bb_middle'] + 2 * df['bb_std']

    return TechnicalIndicatorSnapshot(**df.iloc[-1].to_dict())
```

---

#### Q15: Neo4j 图谱怎么同步的？

**考察点**：图数据库实践

**优秀回答**：
```python
# src/modules/knowledge_center/infrastructure/persistence/neo4j_graph_repository.py
async def sync_full_graph(self, batch_size=100):
    stocks = await self._get_all_stocks()  # PostgreSQL

    for i in range(0, len(stocks), batch_size):
        batch = stocks[i:i+batch_size]

        # 批量创建节点（UNWIND）
        await self._session.execute_write("""
            UNWIND $stocks AS s
            MERGE (stock:Stock {third_code: s.third_code})
            ON CREATE SET stock.name = s.name
        """, stocks=batch)
```

---

#### Q16: Neo4j 约束怎么保证幂等？

**考察点**：幂等性设计

**优秀回答**：
```python
async def ensure_constraints(self):
    # 先查已有约束
    result = await self._session.run("SHOW CONSTRAINTS")
    existing = [r['name'] for r in result]

    # 只创建不存在的约束
    for name, cypher in CONSTRAINTS.items():
        if name not in existing:
            await self._session.run(cypher)
```

**证据**：`src/modules/knowledge_center/infrastructure/persistence/neo4j_graph_repository.py:83`

---

#### Q17: 定时任务怎么实现的？

**考察点**：调度器实践

**优秀回答**：
- **框架**：APScheduler 3.10.4
- **持久化**：任务配置存 PostgreSQL（`scheduler_job_config` 表）
- **启动流程**：
  1. 应用启动时加载持久化配置
  2. 自动注册到调度器
  3. 后台运行

```python
# src/modules/foundation/application/services/scheduler_application_service.py
async def start_scheduler(self):
    await self._scheduler_port.start_scheduler()
    await self._scheduler_port.load_persisted_jobs(job_registry)
```

---

#### Q18: 如果定时任务执行失败怎么办？

**考察点**：容错处理

**优秀回答**：
- **重试机制**：APScheduler 自带重试（`max_instances` 配置）
- **失败记录**：`scheduler_execution_log` 表记录错误信息
- **告警**：（未来）失败超过阈值发送邮件/钉钉

---

### 第四部分：性能与并发（19-24 题）

#### Q19: 异步编程的优缺点？

**考察点**：异步理解

**优秀回答**：
- **优点**：
  - 高并发下资源利用率高
  - IO 阻塞不占用线程
  - 单机可处理更多并发连接
- **缺点**：
  - 调试困难（堆栈深）
  - CPU 密集型任务需卸载到线程池
  - 第三方库可能不兼容

---

#### Q20: 你们有遇到阻塞事件循环的问题吗？

**考察点**：异步踩坑经验

**优秀回答**：
> 有的。Pandas 计算技术指标是同步的，会阻塞事件循环。
>
> 解法是用 `run_in_executor` 放到线程池：
> ```python
> async def compute(self, bars):
>     loop = asyncio.get_event_loop()
>     return await loop.run_in_executor(
>         None,  # 默认线程池
>         self._compute_sync,  # 同步方法
>         bars
>     )
> ```

---

#### Q21: 数据库连接池怎么配置？

**考察点**：连接池调优

**优秀回答**：
```python
create_async_engine(
    ...,
    pool_size=20,          # 基础连接数
    max_overflow=40,       # 最大连接数 = 60
    pool_pre_ping=True,    # 自动检测失效连接
    pool_recycle=3600,     # 1 小时回收
)
```

**调优建议**：
- 根据并发量调整 `pool_size`（QPS/10）
- 监控连接池使用率

---

#### Q22: 有做过压测吗？结果如何？

**考察点**：性能测试经验

**优秀回答**：
> 未正式压测，估算单实例 QPS ~50。
> 瓶颈在 LLM 调用（3-10s 响应）。
>
> 改进方案：
> 1. 缓存分析结果（Redis，1 小时过期）
> 2. 批量分析（一次性分析多只股票）
> 3. 异步任务（用户提交请求后轮询结果）

---

#### Q23: 限流怎么实现的？

**考察点**：限流算法理解

**优秀回答**：
> 使用滑动窗口限流（Sliding Window Log）保护 Tushare API：
> ```python
> class SlidingWindowRateLimiter:
>     async def acquire(self):
>         now = time.monotonic()
>         # 清理窗口外时间戳
>         while self._timestamps and now - self._timestamps[0] >= self._window:
>             self._timestamps.popleft()

>         # 达到上限则等待
>         if len(self._timestamps) >= self._max_calls:
>             wait_time = self._window - (now - self._timestamps[0])
>             await asyncio.sleep(wait_time)

>         self._timestamps.append(now)
> ```

**证据**：`src/modules/data_engineering/infrastructure/external_apis/tushare/rate_limiter.py`

---

#### Q24: 如果 LLM API 超时怎么办？

**考察点**：超时处理

**优秀回答**：
- **当前**：无显式超时（依赖 HTTP 默认超时）
- **改进**：
  ```python
  from httpx import Timeout

  client = OpenAI(
      ...,
      timeout=Timeout(30.0, connect=10.0)  # 总超时 30s，连接 10s
  )
  ```
- **降级**：超时后返回缓存结果 or 简化版分析

---

### 第五部分：事务与一致性（25-28 题）

#### Q25: 数据同步怎么保证幂等性？

**考察点**：幂等性设计

**优秀回答**：
- **数据库层**：唯一约束（ticker + date）
- **业务层**：`sync_task` 表记录已处理股票
- **API 层**：（未来）请求 ID 去重

```sql
INSERT INTO stock_daily_bars (ticker, date, open, close)
VALUES (...)
ON CONFLICT (ticker, date) DO UPDATE SET
    open = EXCLUDED.open,
    close = EXCLUDED.close
```

---

#### Q26: 分布式事务怎么处理？（Neo4j + PG 双写）

**考察点**：分布式事务理解

**优秀回答**：
> 当前未使用分布式事务，通过最终一致性保证：
> 1. 先写 PostgreSQL（主数据）
> 2. 异步同步到 Neo4j（定时任务）
> 3. 失败重试机制
>
> 改进方案：
> - 事件驱动：PG 写入后发布事件，Neo4j 订阅消费
> - Saga 模式：Neo4j 失败时触发补偿事务

---

#### Q27: 重试机制怎么做？

**考察点**：重试模式理解

**优秀回答**：
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),           # 最多重试 3 次
    wait=wait_exponential(min=1, max=60)  # 指数退避 1s/2s/4s
)
async def sync_with_retry():
    ...
```

---

#### Q28: 有考虑过重试风暴吗？

**考察点**：重试风险意识

**优秀回答**：
- **问题**：大量请求同时重试，压垮下游服务
- **解法**：
  - 添加 jitter 随机延迟：`wait_random(0, 1)`
  - 限制并发重试数：信号量控制
  - 熔断器：失败超过阈值后暂停重试

---

### 第六部分：安全与稳定性（29-32 题）

#### Q29: 接口有认证吗？怎么防止滥用？

**考察点**：安全意识

**优秀回答**：
> 当前无认证（内部系统）。
>
> 改进方案：
> 1. JWT 认证：用户登录后获取 token
> 2. 配额管理：免费用户每天 10 次分析
> 3. 限流：每 IP 每分钟 60 次请求

```python
from fastapi.security import HTTPBearer

security = HTTPBearer()

async def get_current_user(creds: HTTPAuthorizationCredentials = Depends(security)):
    token = creds.credentials
    user = await verify_jwt(token)
    return user
```

---

#### Q30: 敏感信息怎么存储？

**考察点**：密钥管理

**优秀回答**：
- **开发环境**：.env 文件（.gitignore 忽略）
- **生产环境**：云厂商 Secrets Manager
- **加密**：密码使用 bcrypt 哈希

---

#### Q31: 有做过熔断吗？

**考察点**：熔断模式理解

**优秀回答**：
> 当前未实现熔断器。
>
> 改进方案：
> ```python
> from circuitbreaker import circuit

> @circuit(failure_threshold=5, recovery_timeout=30)
> async def call_tushare_api():
>     ...
> ```

---

#### Q32: 线上服务挂了怎么发现？

**考察点**：监控告警

**优秀回答**：
- **健康检查**：每 30s `GET /api/v1/health`
- **Prometheus**：QPS/延迟/错误率监控
- **日志告警**：ERROR 日志超过阈值

**证据**：`docker-compose.yml:25-30`

---

### 第七部分：测试与排障（33-36 题）

#### Q33: 单元测试覆盖率多少？

**考察点**：测试意识

**优秀回答**：
> 估计 ~40%，主要集中在 Service 层。
> 目标：核心业务逻辑 >80%。

**证据**：`tests/unit/`

---

#### Q34: 怎么做 Mock 测试？

**考察点**：Mock 实践

**优秀回答**：
```python
from unittest.mock import AsyncMock

async def test_service_with_mock():
    mock_market_quote = AsyncMock()
    mock_market_quote.get_daily_bars.return_value = [DailyBar(...)]

    service = TechnicalAnalystService(mock_market_quote, ...)
    result = await service.run("000001.SZ", date.today())

    assert result.signal in ["BULLISH", "BEARISH", "NEUTRAL"]
    mock_market_quote.get_daily_bars.assert_called_once()
```

---

#### Q35: 线上 CPU 飙高怎么排查？

**考察点**：排障能力

**优秀回答**：
```bash
# 1. 找到占用 CPU 的进程
top -H -p <PID>

# 2. 使用 py-spy 分析
py-spy top --pid <PID>

# 3. 查看线程堆栈
py-spy dump --pid <PID>
```

---

#### Q36: 内存泄露怎么排查？

**考察点**：内存问题排查

**优秀回答**：
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

### 第八部分：系统设计（37-40 题）

#### Q37: 如果让你们系统支持多租户，怎么改？

**考察点**：多租户架构设计

**优秀回答**：
- **数据库层**：添加 `tenant_id` 字段，所有查询加过滤
- **服务层**：从 JWT Token 提取 tenant_id
- **隔离级别**：
  - 方案 A：行级隔离（简单，成本低）
  - 方案 B：独立 Schema（隔离好，运维成本高）

```python
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

#### Q38: 如果要支持每天 100 万次分析请求，怎么设计？

**考察点**：高并发设计

**优秀回答**：
- **QPS 换算**：100 万/86400 ≈ 12 次/秒，考虑峰值 ~100 QPS
- **架构改进**：
  1. 缓存层：Redis 缓存分析结果（命中率目标 80%）
  2. 异步任务：用户提交请求后轮询结果
  3. 水平扩展：Kubernetes HPA 自动扩容（目标 10 实例）
  4. 读写分离：PostgreSQL 主从复制
  5. CDN：静态资源上 CDN

---

#### Q39: 如果 Tushare API 挂了怎么办？

**考察点**：容灾设计

**优秀回答**：
- **短期**：切换到 Akshare（已实现双数据源适配器）
- **中期**：缓存最近 7 天数据，允许离线分析
- **长期**：自建数据仓库，定时同步到本地 PostgreSQL

**证据**：`src/modules/data_engineering/infrastructure/external_apis/akshare/`

---

#### Q40: 如果让你重新设计这个系统，你会做什么不同的选择？

**考察点**：反思与成长

**优秀回答**：
1. **缓存层**：一开始就引入 Redis，减少 LLM 调用
2. **事件驱动**：PG → Neo4j 异步同步（而非定时任务）
3. **认证授权**：从第一天就加上 JWT
4. **监控告警**：第一周就集成 Prometheus
5. **测试覆盖率**：TDD 驱动开发，核心逻辑 >80% 覆盖

---

## 复习清单（按优先级）

### P0（必须掌握）

- [ ] 项目一句话定位（业务目标 + 目标用户）
- [ ] 核心技术栈（FastAPI/SQLAlchemy/Neo4j/LangGraph）
- [ ] 模块化单体架构特点
- [ ] DDD 分层（Domain/Application/Infrastructure/Presentation）
- [ ] 依赖倒置（Port 接口 + 适配器实现）
- [ ] 技术分析接口完整调用链
- [ ] 异步编程优缺点
- [ ] 幂等性保证（唯一约束 + 任务状态表）

### P1（重点复习）

- [ ] Neo4j 图谱同步流程
- [ ] 定时任务实现（APScheduler 持久化）
- [ ] 限流算法（滑动窗口）
- [ ] 重试机制（指数退避）
- [ ] 数据库连接池配置
- [ ] LLM 输出解析（Pydantic 验证）
- [ ] 异常处理（全局中间件）
- [ ] 配置管理（Pydantic Settings）

### P2（加分项）

- [ ] 多 Agent 协作流程
- [ ] 缓存层设计（Redis 方案）
- [ ] 分布式事务（最终一致性）
- [ ] 熔断器模式
- [ ] 监控告警方案
- [ ] 单元测试/Mock 实践
- [ ] 线上故障排查流程
- [ ] 多租户架构设计

---

## 建议补强方向

### 1. 补充缓存层实现

**原因**：面试常问缓存，且能显著提升系统性能

**行动**：
```python
# 添加 Redis 缓存
from redis.asyncio import Redis

class TechnicalAnalystService:
    async def run(self, ticker, date):
        cache_key = f"tech:{ticker}:{date}"
        cached = await self._redis.get(cache_key)
        if cached:
            return json.loads(cached)

        result = await self._analyze(ticker, date)
        await self._redis.setex(cache_key, 3600, json.dumps(result))
        return result
```

---

### 2. 添加 API 认证

**原因**：生产系统必备，面试常考

**行动**：
```python
# 添加 JWT 认证中间件
from fastapi.security import HTTPBearer
from jose import jwt

security = HTTPBearer()

async def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(security)
):
    token = creds.credentials
    payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    return User(**payload)
```

---

### 3. 集成 Prometheus 监控

**原因**：可观测性是生产系统标配

**行动**：
```python
from prometheus_fastapi_instrumentator import Instrumentator

Instrumentator().instrument(app).expose(app)
```

---

### 4. 提升测试覆盖率

**原因**：体现工程质量意识

**行动**：
- 为核心 Service 添加单元测试（目标 >80%）
- 添加 API 层集成测试（Mock 外部依赖）

---

### 5. 准备故障故事

**原因**：面试官喜欢听「踩坑 - 解决 - 复盘」的故事

**准备 3 个故事**：
1. 内存 OOM（定时任务泄露 → 分页 + 背压）
2. LLM API 变更（输出格式变化 → 兼容解析器）
3. Neo4j 约束重复创建（启动报错 → 幂等初始化）
