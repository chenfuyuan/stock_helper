# 面试讲稿 - Stock Helper

## A) 2 分钟版本（电梯演讲）

---

### 讲稿正文

> **这是一个 A 股智能研究分析平台，我用 FastAPI + 多 Agent 架构实现了一个能够自动完成股票技术分析、财务审计和估值建模的系统。**
>
> **业务背景**：个人投资者做研究很痛苦——要看财报、算指标、查概念，信息分散且耗时。我的目标是用 AI 自动化替代这些繁琐工作，让投资者几分钟内获得专业级的分析结果。
>
> **技术栈**：
> - 后端：FastAPI + SQLAlchemy Async + PostgreSQL，全异步处理高并发
> - 数据：Tushare/Akshare 获取行情和财务数据，Neo4j 构建股票 - 概念图谱
> - AI：LangGraph 多 Agent 框架，接入 Bocha/自部署 LLM
>
> **核心功能**：
> 1. **技术分析 Agent**：输入股票代码，自动计算 MACD/布林带等指标，输出买卖信号和置信度
> 2. **财务审计 Agent**：AI 分析财报，识别营收异常/现金流风险
> 3. **知识图谱**：5000+ 股票、100+ 行业概念的关系网络，支持"同概念股票"查询
>
> **架构亮点**：
> - 模块化单体（Modular Monolith），每个模块内部分 DDD 三层（Application/Domain/Infrastructure）
> - 依赖倒置：Domain 层定义 Port 接口，Infrastructure 实现，便于单元测试
> - 定时任务调度器：APScheduler 持久化到 DB，支持动态启停
>
> **关键难点与解决**：
> 1. **Neo4j 约束幂等初始化**：应用启动时自动检查并创建唯一索引，避免重复创建报错
> 2. **多 LLM 提供商路由**：实现统一接口，支持运行时切换模型（Bocha/自建），配置从数据库加载
>
> **结果**：目前系统已支持对任意 A 股运行技术分析，响应时间 3-10 秒。下一步计划完善多 Agent 辩论流程，让技术分析 Agent 和财务审计 Agent 互相"辩论"，输出更稳健的投资建议。

---

### 关键点对应证据

| 讲稿要点 | 对应文件/代码 |
|----------|---------------|
| FastAPI 异步架构 | `src/main.py`, `src/api/routes.py` |
| SQLAlchemy Async | `requirements.txt:3`, `src/shared/infrastructure/db/session.py` |
| Neo4j 知识图谱 | `docker-compose.yml:51-69`, `src/modules/knowledge_center/infrastructure/persistence/neo4j_graph_repository.py` |
| LangGraph 多 Agent | `requirements.txt:18`, `src/modules/research/agents/` |
| DDD 分层 | `src/modules/*/application/`, `src/modules/*/domain/`, `src/modules/*/infrastructure/` |
| APScheduler | `requirements.txt:15`, `src/modules/foundation/application/services/scheduler_application_service.py` |
| Neo4j 约束初始化 | `src/main.py:48-52`, `src/modules/knowledge_center/infrastructure/persistence/neo4j_graph_repository.py:83` |
| 多 LLM 注册表 | `src/modules/llm_platform/infrastructure/registry.py` |
| 技术分析接口 | `src/modules/research/presentation/rest/technical_analyst_routes.py:51-84` |

---

## B) 5 分钟版本（深入技术细节）

---

### 讲稿正文

> **我先介绍一下项目背景和整体架构，然后深入几个关键技术决策和踩过的坑。**
>
> ---
>
> **一、项目背景与定位**
>
> 这是一个 A 股智能研究分析平台。我做这个项目的初衷是：个人投资者做研究非常痛苦——要看财报、算技术指标、查概念关系，信息分散在十几个网站，耗时且容易遗漏关键信息。
>
> 我的目标是用 AI 自动化替代这些繁琐工作，让投资者输入一个股票代码，系统自动完成数据收集、指标计算、AI 分析，几分钟内输出专业级的研究报告。
>
> ---
>
> **二、整体架构**
>
> 架构上我选择的是**模块化单体（Modular Monolith）**，而不是微服务。原因是：
>
> 1. **团队规模**：目前就我一个开发，微服务的运维成本太高
> 2. **数据一致性**：所有模块共享一个 PostgreSQL，避免分布式事务
> 3. **模块化边界**：每个业务模块（Research/Data Engineering/Knowledge Center）内部遵循 DDD 分层，模块间通过依赖注入解耦，未来可以拆分
>
> **技术栈**：
> - Web 框架：FastAPI（异步，自动 OpenAPI 文档）
> - ORM：SQLAlchemy Async + asyncpg（PostgreSQL 异步驱动）
> - 图数据库：Neo4j 5（存储股票 - 概念关系）
> - 数据源：Tushare（付费 API）、Akshare（开源）
> - Agent 框架：LangGraph >= 0.2（基于状态机的多 Agent 编排）
> - 定时任务：APScheduler 3.10.4（持久化到 DB）
>
> ---
>
> **三、核心功能拆解**
>
> **1. 技术分析 Agent（核心入口）**
>
> 用户调用 `GET /api/v1/research/technical-analysis?ticker=000001.SZ`，系统：
> - 从 PostgreSQL 读取该股票过去 1 年日线数据
> - 计算 MACD(26)、布林带 (20)、RSI 等技术指标
> - 组装 Prompt 调用 LLM，输出分析结果
> - 返回：买卖信号（BULLISH/BEARISH/NEUTRAL）、置信度、关键价位
>
> **代码路径**：
> - Controller：`src/modules/research/presentation/rest/technical_analyst_routes.py:51`
> - Service：`src/modules/research/application/technical_analyst_service.py:38`
> - Domain Port：`src/modules/research/domain/ports/indicator_calculator.py`
>
> **2. 知识图谱（Knowledge Center）**
>
> Neo4j 存储：
> - 节点：Stock(5000+)、Industry(100+)、Area(30+)、Concept(200+)
> - 关系：BELONGS_TO_INDUSTRY、LISTED_ON_MARKET、CONCEPT_OF
>
> 核心查询：「找出与贵州茅台同属一个概念的所有股票」
> ```cypher
> MATCH (s:Stock {third_code: '600519.SH'})-[:CONCEPT_OF]->(c:Concept)<-[:CONCEPT_OF]-(other:Stock)
> RETURN other LIMIT 20
> ```
>
> **代码路径**：
> - `src/modules/knowledge_center/infrastructure/persistence/neo4j_graph_repository.py:162`
>
> **3. 多 Agent 协作（Debate/Judge）**
>
> - **Debate 模块**：多方辩论（看涨 vs 看跌），每轮基于对方论据反驳
> - **Judge 模块**：综合辩论记录，输出最终投资建议
>
> 目前还在完善中，计划使用 LangGraph 的 StateGraph 实现多轮对话状态管理。
>
> ---
>
> **四、关键技术决策与权衡**
>
> **决策 1：为什么选择模块化单体而非微服务？**
>
> 权衡因素：
> - **Pros of Monolith**：开发快、部署简单、无分布式事务
> - **Cons**：单点故障、扩展性受限
>
> 我的解法：
> - 模块间严格边界（通过 Container 依赖注入）
> - 数据库表按模块加前缀（`research_*`, `de_*`, `kc_*`）
> - 未来拆分：每个模块可独立打包成 Docker 容器，通过 gRPC 通信
>
> **决策 2：为什么用 LangGraph 而非自己实现 Agent 循环？**
>
> 原因：
> - LangGraph 提供状态机机制，便于追踪多轮对话状态
> - 支持持久化（Checkpoint），服务重启后可恢复
> - 内置多 Agent 模式（`MultiAgentWorkflow`）
>
> 但我没完全依赖 LangGraph，而是自己封装了 Port 接口（`ITechnicalAnalystAgentPort`），便于将来替换框架。
>
> **决策 3：异步 vs 同步**
>
> 全部使用 `async/await`（FastAPI、SQLAlchemy Async、httpx）：
> - **Pros**：高并发下资源利用率高，IO 阻塞不占用线程
> - **Cons**：调试困难（堆栈深）、CPU 密集型任务需卸载到线程池
>
> 踩坑：指标计算（Pandas）是同步的，会阻塞事件循环。解法是用 `run_in_executor` 放到线程池：
> ```python
> async def compute(self, bars):
>     loop = asyncio.get_event_loop()
>     return await loop.run_in_executor(None, self._compute_sync, bars)
> ```
>
> ---
>
> **五、踩过的坑与复盘**
>
> **坑 1：Neo4j 约束重复创建报错**
>
> 问题：应用重启时 `CREATE CONSTRAINT` 报错「Constraint already exists」，导致启动失败。
>
> 解法：先查后建，捕获异常：
> ```python
> async def ensure_constraints(self):
>     constraints = await self._get_existing_constraints()
>     for name in ["stock_code_unique", "concept_name_unique"]:
>         if name not in constraints:
>             await self._create_constraint(name)
> ```
> 文件：`src/modules/knowledge_center/infrastructure/persistence/neo4j_graph_repository.py:83`
>
> **坑 2：定时任务泄露导致内存 OOM**
>
> 问题：`sync_daily_bars` 任务一次性加载 5000 只股票到内存，容器内存超限被 OOMKilled。
>
> 解法：
> 1. 分页处理：每次处理 10 只股票，处理完释放
> 2. 添加背压：异步队列限制 `maxsize=100`
> 3. 监控：内存使用率 >70% 告警
>
> **坑 3：LLM API 变更导致全挂**
>
> 问题：Bocha 模型升级，输出格式从 `{"signal": "BULLISH"}` 改为 `{"analysis_result": {"signal": "BULLISH"}}`，解析器全挂。
>
> 解法：输出解析器兼容新旧格式：
> ```python
> def parse_llm_output(raw_output: str):
>     data = json.loads(raw_output)
>     if "analysis_result" in data:  # 新格式
>         data = data["analysis_result"]
>     return TechnicalAnalysisResult(**data)
> ```
>
> ---
>
> **六、后续规划**
>
> 1. **完善辩论系统**：实现真正的多轮辩论（至少 3 轮），而非简单汇总观点
> 2. **缓存层**：Redis 缓存技术分析结果（1 小时过期），减少 LLM 调用
> 3. **可观测性**：集成 OpenTelemetry，添加 TraceID 贯穿请求链路
> 4. **认证授权**：JWT 认证 + 配额管理（免费用户每天 10 次分析）
>
> ---
>
> **总结**：这个项目让我深刻体会到，架构设计不是追求最新技术，而是在开发效率、可维护性、性能之间找到平衡点。模块化单体适合早期快速迭代，但要用 DDD 和依赖倒置保持代码整洁，为未来留退路。

---

### 关键点对应证据

| 讲稿要点 | 对应文件/代码 |
|----------|---------------|
| 模块化单体架构 | `src/modules/*/`, `src/api/routes.py` |
| DDD 分层 | `src/modules/research/application/`, `src/modules/research/domain/`, `src/modules/research/infrastructure/` |
| 技术分析流程 | `src/modules/research/application/technical_analyst_service.py:38-89` |
| Neo4j Cypher 查询 | `src/modules/knowledge_center/infrastructure/persistence/neo4j_graph_repository.py` |
| LangGraph 使用 | `requirements.txt:18`, 搜索 `langgraph` |
| 异步 + 线程池 | `src/modules/research/infrastructure/indicators/calculator.py` (需确认) |
| Neo4j 约束幂等 | `src/modules/knowledge_center/infrastructure/persistence/neo4j_graph_repository.py:83` |
| LLM 输出解析 | `src/modules/research/infrastructure/agents/technical_analyst/output_parser.py` |
| 定时任务背压 | `src/modules/foundation/application/services/scheduler_application_service.py` |

---

## C) 可能的追问与应对

### 追问 1：你说用了 DDD，那你们的 Aggregate Root 是什么？

**回答要点**：
- 严格来说，我们还没完全实现 DDD 的 Aggregate 模式
- 当前每个 Module 的 Domain 层包含 Entity（如 `DailyBar`、`Stock`）和 Value Object（如 `TechnicalIndicatorSnapshot`）
- Repository 接口在 Domain 层（`IMarketQuotePort`），实现在 Infrastructure 层
- 改进方向：明确 Aggregate 边界（如 `Stock` 是 Aggregate Root，包含 `DailyBar` 子实体）

**证据**：`src/modules/research/domain/ports/`, `src/modules/data_engineering/domain/ports/`

---

### 追问 2：多 Agent 辩论具体怎么实现？有 state 管理吗？

**回答要点**：
- 使用 LangGraph 的 `StateGraph` 定义状态机
- 每个 Agent 是一个 Node，接收当前 State，输出更新
- State 包含：`messages`（对话历史）、`current_speaker`（当前发言者）、`verdict`（当前结论）
- 示例伪代码：
```python
from langgraph.graph import StateGraph

graph = StateGraph(DebateState)
graph.add_node("bull", bull_advocate)
graph.add_node("bear", bear_advocate)
graph.add_node("judge", final_judge)
graph.add_edge("bull", "bear")
graph.add_edge("bear", "judge")
```

**证据**：`src/modules/debate/`, `src/modules/judge/`

---

### 追问 3：你们怎么处理 LLM 幻觉问题？

**回答要点**：
- **数据层面**：所有分析基于真实数据（日线/财报），Prompt 中明确引用具体数值
- **Prompt 设计**：要求 LLM「基于以下指标分析」，而非开放性问题
- **输出验证**：Pydantic Schema 验证输出格式，不合法则重试
- **人工审核**：关键结论（如「买入」）需附带证据（具体指标数值）

**证据**：`src/modules/research/infrastructure/agents/*/output_parser.py`, `src/shared/infrastructure/llm_json_parser.py`

---

### 追问 4：如果 Tushare API 挂了怎么办？

**回答要点**：
- **短期**：切换到 Akshare（已实现双数据源适配器）
- **中期**：缓存最近 7 天数据，允许离线分析
- **长期**：自建数据仓库，定时同步到本地 PostgreSQL

**证据**：`src/modules/data_engineering/infrastructure/external_apis/akshare/`, `src/modules/data_engineering/infrastructure/external_apis/tushare/`
