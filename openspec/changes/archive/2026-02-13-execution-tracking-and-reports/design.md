## Context

当前研究流水线（Coordinator → Research → Debate → Judge）全程内存传递，结果仅通过 HTTP 返回后丢失。所有 Agent 仅输出结构化 JSON，无人类可读报告。LLM 调用（经 `LLMService.generate()`）和外部 API 调用（经 `WebSearchService.search()`）均无审计留痕。

已有基础设施：PostgreSQL + SQLAlchemy async + Alembic 迁移 + `BaseRepository` 泛型基类 + DI 容器（各模块 `container.py`）。LangGraph `StateGraph` 编排研究流程，节点工厂模式（`create_expert_node` 等）。

**约束**：严格 DDD 分层；模块间仅通过 Port/Application 接口通信；不跨模块依赖 infrastructure。

## Goals / Non-Goals

**Goals:**

- 研究流水线每次执行（含失败）的业务结果完整持久化，支持历史查询与回溯
- LLM 调用的完整 prompt/completion/token 用量/耗时自动审计，无需各模块自行实现
- 外部 API 调用（博查搜索）的请求/响应自动记录
- 三层数据通过 `session_id` 松耦合关联，可串联排查完整链路
- 9 个 Agent 同时产出结构化 JSON 与叙述性中文报告
- 上下文传递不污染任何模块的 Port 签名

**Non-Goals:**

- 不做实时监控/告警（属于运维层，不在本次范围）
- 不做 prompt 版本管理或 A/B 测试（未来独立 change）
- 不做数据保留策略的自动清理（可手动或后续迭代）
- 不改变 LangGraph 图结构或编排流程本身
- 不引入新的外部依赖（消息队列、Elasticsearch 等）

## Decisions

### D1: 三层持久化各归其主

**决策**：业务执行追踪归 Coordinator，LLM 调用审计归 llm_platform，外部 API 日志归 llm_platform（当前唯一的外部 API 出口），三层均通过 Port 抽象隔离存储实现。

**为什么不全放 Coordinator**：Coordinator 的边界是「流程编排 + 状态治理」，不应知道 prompt 结构、token 用量或 HTTP 请求细节。将审计日志放在产生调用的模块中，符合「谁产生谁记录」原则，且新增 LLM 消费方时自动获得审计能力。

**为什么外部 API 日志放 llm_platform 而非 shared**：当前研究流水线中唯一的外部 API 调用是博查搜索，已通过 `llm_platform` 的 `WebSearchService` 对外暴露。将 `ExternalAPICallLog` 模型定义在 `shared/infrastructure/` 中（供未来其他模块复用），但拦截逻辑在 `WebSearchService` 内实现。

**备选（已否决）**：全放 Coordinator 的单一 `subtask` 表——导致 Coordinator 需 import prompt 结构，破坏边界。

### D2: 拦截点选择 — Application 层门面

**决策**：

| 层 | 拦截点 | 理由 |
|----|--------|------|
| LLM 审计 | `LLMService.generate()` | 所有模块的 LLM 调用最终都经过此 Application 门面；可获取 `alias`/`tags` 路由信息 |
| 外部 API | `WebSearchService.search()` | 所有博查搜索经过此入口；可获取完整 request/response |

在 Application 层拦截而非 Infrastructure 层（如 `OpenAIProvider`）的原因：Application 层是模块对外的统一入口，拦截一处即覆盖所有 Provider 实现。若在 Provider 层拦截，每新增一个 Provider 都需加拦截代码。

**实现方式**：在 `LLMService.generate()` 和 `WebSearchService.search()` 方法内部，调用前记录开始时间，调用后（含异常）记录结果并通过 Repository 异步写入。通过 `contextvars` 获取可选的 `session_id`，无上下文时 `session_id` 为 null（非研究流水线的 LLM 调用也能记录，只是无关联）。

### D3: 上下文传递 — `contextvars` 隐式传播

**决策**：在 `src/shared/infrastructure/` 中定义 `ExecutionContext`（Pydantic BaseModel，含 `session_id`）和 `ContextVar`。Coordinator 在编排入口设置，LLM/API 层隐式读取。

```python
# src/shared/infrastructure/execution_context.py
import contextvars
from pydantic import BaseModel

class ExecutionContext(BaseModel):
    session_id: str

current_execution_ctx: contextvars.ContextVar[ExecutionContext | None] = (
    contextvars.ContextVar("current_execution_ctx", default=None)
)
```

**为什么不用显式参数**：需在 `ILLMPort.generate()`、`IWebSearchProvider.search()` 等所有 Port 签名上加 `session_id` 参数，违反依赖倒置（下游 Port 不应知道上游编排概念）。

**为什么不用中间件/AOP**：Python 异步生态中 `contextvars` 天然支持 `asyncio.Task` 上下文继承，LangGraph 并行节点（5 专家 fan-out）各自继承父上下文，无需额外处理。中间件模式在非 HTTP 的 LangGraph 内部调用链中不适用。

**async 安全性**：Python 3.10+ 的 `contextvars` 在 `asyncio` 中每个 Task 拥有独立的上下文副本（`copy_context()`），并行专家节点不会互相干扰。

### D4: LangGraph 节点持久化 — 装饰器包装

**决策**：不修改现有节点工厂（`create_expert_node` 等）的业务逻辑，而是在 `graph_builder.py` 中用一个 `persist_node_execution` 高阶函数包装节点函数。

```python
def persist_node_execution(
    node_fn: Callable,
    node_type: str,
    session_repo: IResearchSessionRepository,
) -> Callable:
    """
    节点持久化装饰器：记录开始时间、执行节点、记录结果/错误、写入 NodeExecution。
    """
    async def wrapper(state: ResearchGraphState) -> dict[str, Any]:
        ctx = current_execution_ctx.get()
        started_at = datetime.utcnow()
        try:
            result = await node_fn(state)
            # 持久化成功结果
            ...
            return result
        except Exception as e:
            # 持久化失败信息
            ...
            raise
    return wrapper
```

**为什么不在 `langgraph_orchestrator.py` 的 `run()` 方法中后处理**：`graph.ainvoke()` 只返回最终 state，丢失了各节点的独立耗时和中间错误。用装饰器可以在每个节点粒度捕获 started_at / completed_at / error。

**为什么不用 LangGraph 的 callback 机制**：LangGraph 的 `astream_events` 等 API 更适合流式展示，对持久化来说 callback 的事件格式不稳定且携带信息有限。装饰器更直接、更可控。

### D5: Agent 叙述性报告 — JSON 内嵌 narrative_report 字段

**决策**：在 Agent 的 Prompt 中要求 LLM 在现有 JSON 输出中新增 `narrative_report` 字段（string 类型），包含完整的中文叙述性分析报告。各 DTO 相应新增 `narrative_report: str` 字段。

**为什么不用两段式输出（JSON + Markdown 分隔）**：增加 output_parser 的复杂度，需要分割两种格式；且 LLM 可能在格式边界处出错。单一 JSON 结构内嵌字符串字段最简单、最可靠。

**为什么不用两次 LLM 调用（先 JSON 再生成报告）**：成本翻倍、延迟翻倍、两次调用间可能不一致。

**narrative_report 的内容要求**：Prompt 中明确指示报告应包含：核心结论、关键论据、风险提示、置信度说明。长度约 300-800 字。语言为中文。

### D6: 存储方案 — PostgreSQL + Port 抽象

**决策**：四张表均使用 PostgreSQL 存储，大体积字段（prompt/completion/response_data）使用 `TEXT` 类型（非 JSONB，因不需要在这些字段上做 JSON 查询）。通过 Repository Port 隔离实现。

**数据模型**：

**research_sessions**（Coordinator 模块）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID, PK | 会话唯一标识 |
| symbol | VARCHAR(20) | 股票代码 |
| status | VARCHAR(20) | running / completed / partial / failed |
| selected_experts | JSONB | 选中的专家列表 |
| options | JSONB | 执行选项 |
| trigger_source | VARCHAR(50) | 触发来源（api / scheduler） |
| created_at | TIMESTAMP | 创建时间 |
| completed_at | TIMESTAMP, nullable | 完成时间 |
| duration_ms | INTEGER, nullable | 总耗时（毫秒） |

**node_executions**（Coordinator 模块）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID, PK | 记录唯一标识 |
| session_id | UUID, FK | 关联 research_sessions |
| node_type | VARCHAR(50) | technical_analyst / financial_auditor / ... / debate / judge |
| status | VARCHAR(20) | success / failed / skipped |
| result_data | JSONB, nullable | 结构化业务结果 |
| narrative_report | TEXT, nullable | 文字报告 |
| error_type | VARCHAR(100), nullable | 异常类名 |
| error_message | TEXT, nullable | 错误详情 |
| started_at | TIMESTAMP | 开始时间 |
| completed_at | TIMESTAMP, nullable | 结束时间 |
| duration_ms | INTEGER, nullable | 节点耗时 |

**llm_call_logs**（llm_platform 模块）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID, PK | 记录唯一标识 |
| session_id | UUID, nullable | 关联 session（无上下文时为 null） |
| caller_module | VARCHAR(50) | 调用方模块名 |
| caller_agent | VARCHAR(50), nullable | 调用方 Agent 标识 |
| model_name | VARCHAR(100) | 模型名称 |
| vendor | VARCHAR(50) | 供应商 |
| prompt_text | TEXT | 完整 user prompt |
| system_message | TEXT, nullable | system prompt |
| completion_text | TEXT | LLM 完整输出 |
| prompt_tokens | INTEGER, nullable | prompt token 数 |
| completion_tokens | INTEGER, nullable | completion token 数 |
| total_tokens | INTEGER, nullable | 总 token 数 |
| temperature | FLOAT | 温度参数 |
| latency_ms | INTEGER | 调用耗时 |
| status | VARCHAR(20) | success / failed |
| error_message | TEXT, nullable | 错误信息 |
| created_at | TIMESTAMP | 记录时间 |

**external_api_call_logs**（模型定义在 shared，拦截在 llm_platform）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID, PK | 记录唯一标识 |
| session_id | UUID, nullable | 关联 session |
| service_name | VARCHAR(50) | 服务名（bochai / tushare / ...） |
| operation | VARCHAR(100) | 操作（web-search / ...） |
| request_params | JSONB | 请求参数 |
| response_data | TEXT | 完整响应（大体积） |
| status_code | INTEGER, nullable | HTTP 状态码 |
| latency_ms | INTEGER | 调用耗时 |
| status | VARCHAR(20) | success / failed |
| error_message | TEXT, nullable | 错误信息 |
| created_at | TIMESTAMP | 记录时间 |

**索引策略**：`research_sessions` 在 `(symbol, created_at)` 上建组合索引；`node_executions` 在 `session_id` 上建索引；`llm_call_logs` 和 `external_api_call_logs` 在 `(session_id, created_at)` 上建组合索引。

### D7: 历史查询 API 设计

**决策**：在 Coordinator 的 Presentation 层新增查询端点，聚合三层数据返回。

| 端点 | 方法 | 说明 |
|------|------|------|
| `/research/sessions` | GET | 会话列表（分页，支持 symbol / 时间范围过滤） |
| `/research/sessions/{session_id}` | GET | 会话详情 + 全部 NodeExecution |
| `/research/sessions/{session_id}/llm-calls` | GET | 关联的 LLM 调用日志 |
| `/research/sessions/{session_id}/api-calls` | GET | 关联的外部 API 调用日志 |

LLM 和 API 日志的查询通过 llm_platform/shared 的 Application 接口完成（Coordinator 不直接查对方的 Repository），Coordinator 调用对方的查询服务并聚合返回。

### D8: 持久化写入策略 — 异步非阻塞

**决策**：Layer 2/3 的日志写入采用「尽力而为」策略——写入失败不阻塞主流程，仅记录 warning 日志。Layer 1 的业务追踪写入如果失败，同样不阻塞研究流水线主流程（但会记录 error 日志）。

**理由**：研究流水线的核心价值是产出分析结果，日志/审计是辅助能力。如果因为日志写入失败导致整个研究失败，得不偿失。

## Risks / Trade-offs

**[R1: contextvars 隐式传递的可维护性]** → 通过 `ExecutionContext` 类型定义和清晰的 docstring 文档化约定；在 Coordinator 的设置和重置逻辑中使用 try/finally 确保上下文正确清理。

**[R2: 大体积数据导致 PostgreSQL 膨胀]** → 短期通过 `TEXT` 类型 + TOAST 自动处理；Port 抽象已预留，规模增长时可切换为文件存储。可考虑在 `llm_call_logs` 表上按月分区（Partition by Range on `created_at`）。

**[R3: 持久化装饰器增加节点耗时]** → 数据库写入通常 < 10ms，相对 LLM 调用的数秒耗时可忽略。且采用异步写入，不阻塞节点间的状态传递。

**[R4: Prompt 改造可能影响现有 JSON 输出质量]** → 新增 `narrative_report` 字段是纯增量变更，不修改现有字段的定义或约束。分专家逐步改造（而非一次性改 9 个），每改一个验证 JSON 解析不受影响。

**[R5: LLM 调用日志中 caller_module / caller_agent 的标识]** → 依赖 `contextvars` 传递或在 `LLMService.generate()` 方法签名中新增可选的 `caller_module`/`caller_agent` 参数（这两个参数属于日志元数据，不是领域概念，加在 Application 层门面上可接受）。

## Migration Plan

1. **数据库迁移**：单个 Alembic revision 创建 4 张新表，纯增量操作，不影响现有表。
2. **部署步骤**：`alembic upgrade head` → 部署新代码。因为是新增表和新增逻辑，无需回填数据。
3. **回滚策略**：`alembic downgrade` 删除 4 张新表；代码回滚后持久化逻辑不再触发，功能静默退化为原始行为（内存传递 + HTTP 返回）。
4. **渐进式上线**：可先部署 `execution-context-propagation` + `llm-call-audit`（最小侵入），验证无误后再上 `pipeline-execution-tracking` + `agent-narrative-reports`。

## Open Questions

1. **caller_module / caller_agent 的传递方式**：是扩展 `ExecutionContext` 加入调用方信息，还是在 `LLMService.generate()` 签名中新增可选参数？前者更自动但信息可能不准确（同一 context 下多个 agent 调用），后者更显式但需各调用方配合传参。
2. **narrative_report 长度控制**：是否需要在 Prompt 中硬性限制字数（如 500 字以内），还是让 LLM 自由发挥？过短可能信息不足，过长增加 token 消耗和存储。
