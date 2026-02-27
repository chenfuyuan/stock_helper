# 项目全景分析 - Stock Helper

## 1. 项目一句话定位

**Stock Helper** 是一个面向 A 股投资者的智能研究分析平台，通过多 Agent 协作系统自动完成股票的技术分析、基本面审计、估值建模和概念图谱分析，帮助投资者快速生成专业的投资研究报告。

**业务目标**：降低个人投资者的研究门槛，用 AI 自动化替代人工完成繁琐的数据收集、指标计算和初步分析工作。

---

## 2. 核心功能清单（按重要性排序）

| 优先级 | 功能模块 | 描述 |
|--------|----------|------|
| P0 | **技术分析 Agent** | 对指定股票进行技术指标分析，输出买卖信号和置信度 |
| P0 | **数据工程** | 自动化同步 A 股日线数据、概念数据、财务数据（Tushare/Akshare） |
| P1 | **财务审计 Agent** | 对上市公司财报进行 AI 审计，识别潜在风险 |
| P1 | **概念图谱 (Knowledge Center)** | 基于 Neo4j 构建股票 - 概念 - 行业的知识图谱 |
| P1 | **估值建模 Agent** | 对股票进行 DCF/相对估值建模 |
| P2 | **辩论系统 (Debate)** | 多 Agent 辩论形成更稳健的投资判断 |
| P2 | **决策系统 (Judge)** | 综合多方观点输出最终投资建议 |
| P2 | **市场洞察** | 涨停分析、板块热度、概念热度分析 |
| P3 | **定时任务调度** | 基于 APScheduler 的数据同步定时任务 |

---

## 3. 主要模块/包/目录结构

### 关键 10 个模块及职责

```
src/
├── main.py                              # 应用启动入口，FastAPI 应用初始化
├── api/
│   ├── routes.py                        # API 路由总入口，注册所有模块的 router
│   ├── health.py                        # 健康检查接口
│   └── middlewares/
│       └── error_handler.py             # 全局异常处理中间件
├── modules/
│   ├── data_engineering/                # 数据工程模块（P0）
│   │   ├── application/                 # 应用层：数据同步服务
│   │   ├── infrastructure/              # 基础设施：Tushare/Akshare 适配器
│   │   └── presentation/rest/           # API 接口
│   │
│   ├── research/                        # 研究分析模块（P0）
│   │   ├── agents/                      # 各分析 Agent 定义
│   │   │   ├── technical_analyst/       # 技术分析 Agent
│   │   │   ├── financial_auditor/       # 财务审计 Agent
│   │   │   └── valuation_modeler/       # 估值建模 Agent
│   │   ├── application/                 # 应用服务层
│   │   └── infrastructure/              # 指标计算/LLM 输出解析
│   │
│   ├── knowledge_center/                # 知识图谱模块（P1）
│   │   ├── infrastructure/neo4j/        # Neo4j 图数据库操作
│   │   └── presentation/rest/graph_router.py
│   │
│   ├── llm_platform/                    # LLM 平台模块（基础设施）
│   │   ├── application/services/
│   │   └── infrastructure/registry.py   # 多 LLM 提供商注册表
│   │
│   ├── coordinator/                     # 协调器模块（Agent 编排）
│   ├── debate/                          # 辩论系统模块
│   ├── judge/                           # 决策系统模块
│   └── market_insight/                  # 市场洞察模块
│
├── shared/                              # 共享基础设施
│   ├── config.py                        # 全局配置类 (Settings)
│   ├── domain/                          # 共享领域模型
│   ├── application/                     # 共享应用服务
│   └── infrastructure/                  # 共享基础设施（日志/HTTP 客户端）
│
└── alembic/                             # 数据库迁移脚本

openspec/                                # 需求规格说明书（OpenSpec 规范）
└── changes/
    ├── archive/                         # 已归档的变更文档
    └── active/                          # 进行中的变更
```

---

## 4. 技术栈与关键依赖

### 核心框架与库

| 类别 | 技术选型 | 文件证据 |
|------|----------|----------|
| Web 框架 | **FastAPI** (异步) | `requirements.txt`, `src/main.py` |
| ASGI 服务器 | **Uvicorn** | `requirements.txt` |
| ORM | **SQLAlchemy (Async)** | `requirements.txt` |
| 数据库 | **PostgreSQL 15** | `docker-compose.yml` |
| 图数据库 | **Neo4j 5** | `docker-compose.yml`, `requirements.txt` |
| 数据源 | **Tushare**, **Akshare** | `requirements.txt`, `.env` |
| LLM SDK | **OpenAI** (兼容接口) | `requirements.txt` |
| Agent 框架 | **LangGraph** (>=0.2) | `requirements.txt` |
| 定时任务 | **APScheduler 3.10.4** | `requirements.txt` |
| 依赖注入 | **Dependency-Injector** | `requirements.txt` |
| 日志 | **Loguru**, **Structlog** | `requirements.txt` |
| 数据处理 | **Pandas** | `requirements.txt` |
| 监控 | **Prometheus Client** | `requirements.txt` |

### 开发工具

```
pytest, pytest-asyncio, pytest-cov  # 测试框架
mypy                                # 类型检查
black, isort                        # 代码格式化
flake8                              # 代码规范检查
```

---

## 5. 系统架构推断

### 架构类型：**模块化单体 (Modular Monolith)**

**判断依据**：

1. **单一代码仓库**：所有模块在同一 repo 中，共享 `src/shared/` 基础设施
2. **模块间直接调用**：通过依赖注入容器获取服务，非 RPC/消息队列通信
3. **共享数据库**：所有模块共用一个 PostgreSQL 实例（通过 schema 或表名前缀区分）
4. **统一入口**：单一 FastAPI 应用 (`src/main.py`) 注册所有路由
5. **模块化边界**：每个业务模块 (`modules/*`) 内部遵循 DDD 分层（application/infrastructure/presentation）

### 架构图（推断）

```
┌─────────────────────────────────────────────────────────────┐
│                      FastAPI Application                     │
│                      (src/main.py)                           │
├─────────────────────────────────────────────────────────────┤
│  API Router (src/api/routes.py)                              │
│  ├── /api/v1/health                                          │
│  ├── /api/v1/research/*   → research module                  │
│  ├── /api/v1/stocks/*     → data_engineering module          │
│  ├── /api/v1/graph/*      → knowledge_center module          │
│  ├── /api/v1/scheduler/*  → foundation module                │
│  └── ...                                                     │
├─────────────────────────────────────────────────────────────┤
│  Modules (src/modules/)                                      │
│  ┌─────────────┬─────────────┬─────────────┬─────────────┐  │
│  │ data_eng    │ research    │ knowledge   │ llm_platform│  │
│  │             │             │ _center     │             │  │
│  ├─────────────┼─────────────┼─────────────┼─────────────┤  │
│  │ coordinator │ debate      │ judge       │ market_     │  │
│  │             │             │             │ insight     │  │
│  └─────────────┴─────────────┴─────────────┴─────────────┘  │
├─────────────────────────────────────────────────────────────┤
│  Shared Infrastructure (src/shared/)                         │
│  ├── config.py (Settings)                                    │
│  ├── domain/ (共享实体/值对象)                                │
│  └── infrastructure/ (DB 连接/HTTP 客户端/日志)                 │
└─────────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
   ┌────────────┐      ┌────────────┐      ┌────────────┐
   │ PostgreSQL │      │   Neo4j    │      │ Tushare/   │
   │  (数据库)   │      │  (图数据库) │      │ Akshare    │
   └────────────┘      └────────────┘      └────────────┘
```

---

## 6. 入口点

### 应用启动入口

**文件**: `src/main.py:68-91`

```python
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    lifespan=lifespan,
)

# 注册 API 路由
app.include_router(api_router, prefix=settings.API_V1_STR)
```

### Lifespan 事件（应用生命周期）

**文件**: `src/main.py:20-65`

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动事件
    logger.info("Application starting up...")

    # 1. 启动调度器
    scheduler_service = get_scheduler_service()
    await scheduler_service.start_scheduler()

    # 2. 加载持久化的调度配置
    job_registry = get_job_registry()
    await scheduler_service.load_persisted_jobs(job_registry)

    # 3. 初始化 LLM 注册表
    await LLMPlatformStartup.initialize()

    # 4. 初始化 Knowledge Center 图谱约束
    await KnowledgeCenterContainer().graph_repository().ensure_constraints()

    yield  # 应用运行中

    # 关闭事件
    await scheduler_service.shutdown_scheduler()
    close_knowledge_center_driver()
```

### 主要 Controllers/Routers

**文件**: `src/api/routes.py:1-32`

| 路由前缀 | 模块 | 文件路径 |
|----------|------|----------|
| `/api/v1/health` | Health | `src/api/health.py` |
| `/api/v1/research` | Research | `src/modules/research/presentation/rest/` |
| `/api/v1/stocks` | Data Engineering | `src/modules/data_engineering/presentation/rest/` |
| `/api/v1/graph` | Knowledge Center | `src/modules/knowledge_center/presentation/rest/graph_router.py` |
| `/api/v1/scheduler` | Foundation | `src/modules/foundation/presentation/rest/scheduler_routes.py` |
| `/api/v1/debate` | Debate | `src/modules/debate/presentation/rest/` |
| `/api/v1/judge` | Judge | `src/modules/judge/presentation/rest/` |
| `/api/v1/market-insight` | Market Insight | `src/modules/market_insight/presentation/rest/` |

---

## 7. "两分钟面试口述版"总结

> **这是一个 A 股智能研究分析平台，我用 FastAPI + 多 Agent 架构实现了一个能够自动完成股票技术分析、财务审计和估值建模的系统。**
>
> **技术栈上**，后端用 FastAPI + SQLAlchemy Async + PostgreSQL 处理 REST API，用 Neo4j 存储股票 - 概念 - 行业的知识图谱，数据源接入 Tushare 和 Akshare。核心创新点是引入了 LangGraph 框架实现多 Agent 协作——技术分析 Agent、财务审计 Agent、估值建模 Agent 各自独立工作，最后通过 Debate 辩论系统形成共识，由 Judge 模块输出最终投资建议。
>
> **架构设计**上，我采用模块化单体（Modular Monolith），每个业务模块（research/data_engineering/knowledge_center 等）内部遵循 DDD 分层（application/infrastructure/presentation），模块间通过依赖注入解耦。定时任务用 APScheduler 实现数据自动同步，支持 cron 表达式配置并持久化到数据库。
>
> **关键难点**有两个：一是 Neo4j 图谱约束的幂等初始化（应用启动时自动检查并创建约束，避免重复报错）；二是多 LLM 提供商的动态注册表（支持切换 Bocha/自部署模型，配置从数据库加载）。
>
> **目前**系统支持对任意 A 股股票运行技术分析，输入 ticker 和分析日期，输出买卖信号、置信度、关键价位和风险提醒。下一步计划完善 Debate 辩论流程，让多个 Agent 能够就"是否值得投资"进行多轮辩论，提升决策质量。

---

## 附录：关键文件索引

| 文件 | 路径 | 用途 |
|------|------|------|
| 应用入口 | `src/main.py` | FastAPI 应用初始化 |
| 路由注册 | `src/api/routes.py` | 所有 API 路由入口 |
| 配置类 | `src/shared/config.py` | 全局 Settings 类 |
| 环境变量 | `.env` | 数据库/LLM/Tushare 配置 |
| Docker 编排 | `docker-compose.yml` | App/Postgres/Neo4j 三容器 |
| 依赖清单 | `requirements.txt` | Python 依赖 |
| 项目配置 | `pyproject.toml` | Black/Mypy/Pytest 配置 |
