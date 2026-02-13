## Why

当前研究流水线（Coordinator → Research → Debate → Judge）的全部执行结果仅在内存中传递，通过 HTTP 一次性返回后即丢失。这带来三个核心问题：

1. **不可追溯**：无法回溯任何一次研究的中间过程和最终裁决，无法评估历史推荐的准确性，也无法为后续的「动态专家权重」等优化提供数据基础。
2. **不可审计**：LLM 的完整 prompt 与 completion、外部 API（如博查搜索）的请求与响应均未留痕，无法排查幻觉来源、复现问题、或优化 prompt。
3. **可读性差**：所有 Agent 仅输出结构化 JSON，缺乏面向人类的叙述性报告。用户和投研团队需要直接阅读分析结论，而非自行解读 JSON 字段。

解决这三个问题是系统从「可用原型」迈向「可运营产品」的关键一步。

## What Changes

### 三层持久化架构

采用分层持久化策略，各层职责清晰、互不越界，通过 `session_id` 松耦合关联：

- **Layer 1 — 业务执行追踪（Coordinator 职责）**：引入 `ResearchSession`（一次完整研究会话）和 `NodeExecution`（各节点执行快照）领域模型。LangGraph 每个节点完成（含失败）后，自动将业务级结果（结构化 JSON + 文字报告）、执行状态、错误信息持久化。**失败节点同样持久化，记录 error_type 和 error_message。**
- **Layer 2 — LLM 调用审计（llm_platform 职责）**：在 `llm_platform` 模块新增 `LLMCallLog`，统一记录所有 LLM 调用的完整 prompt、completion、token 用量、耗时与状态。任何模块的 LLM 调用自动获得审计能力，无需各模块自行实现。
- **Layer 3 — 外部 API 调用日志（shared infrastructure）**：新增 `ExternalAPICallLog`，记录博查等外部 API 的请求参数、响应数据、耗时与状态。由各模块的 infrastructure adapter 负责记录。

### 上下文传递机制

使用 Python `contextvars` 在 Coordinator 编排入口设置 `ExecutionContext`（含 `session_id`），下游模块（Research/Debate/Judge）的业务接口无感知，`llm_platform` 和外部 API adapter 隐式读取上下文完成关联，不污染任何模块的 Port 签名。

### Agent 叙述性报告

改造 Research（五专家）、Debate（多空+消解）、Judge（裁决）三个模块共 9 个 Agent 的输出格式，采用「双输出模式」——单次 LLM 调用同时产出结构化 JSON（供程序消费）和叙述性中文报告（供人类阅读）。

### 历史查询 API

提供 REST 接口查询历史研究会话列表及详情（含各节点报告），支持按 symbol、时间范围筛选。可下钻查看关联的 LLM 调用日志和外部 API 调用日志。

### 存储策略

三层数据均先用 PostgreSQL 存储（当前规模完全够用），但通过 Port 抽象隔离存储实现。Layer 2/3 的大体积字段（prompt/completion/response）使用 TEXT 类型，未来规模增长时可无缝切换为文件存储/对象存储，业务代码不受影响。

## Capabilities

### New Capabilities

- `pipeline-execution-tracking`: 研究流水线业务执行追踪（Layer 1）。包括 ResearchSession / NodeExecution 领域建模、Repository Port 与 PostgreSQL 实现、失败持久化（error_type + error_message）、数据库迁移、LangGraph 编排层集成回调、历史查询 API。
- `llm-call-audit`: LLM 调用审计（Layer 2）。在 llm_platform 模块新增 LLMCallLog 模型与 Repository，自动记录所有 LLM 调用的完整 prompt/completion/token 用量/耗时/状态，通过 contextvars 关联 session_id。
- `external-api-call-logging`: 外部 API 调用日志（Layer 3）。在 shared infrastructure 新增 ExternalAPICallLog 模型与通用日志装饰器/中间件，各模块的外部 API adapter 自动记录请求/响应/耗时/状态。
- `execution-context-propagation`: 执行上下文传递机制。基于 Python contextvars 实现 ExecutionContext（session_id 等），Coordinator 设置、下游模块隐式消费，不侵入 Port 接口。
- `agent-narrative-reports`: Agent 叙述性报告能力。各 Agent Prompt 改造、DTO 扩展（新增 narrative_report 字段）、output_parser 适配，使每个 Agent 在输出结构化数据的同时生成人类可读的中文分析报告。

### Modified Capabilities

（无现有 spec 层面的需求变更）

## Impact

- **Coordinator 模块**（`src/modules/coordinator/`）：新增 ResearchSession / NodeExecution 领域模型、Repository Port + 实现、LangGraph 编排回调、ExecutionContext 设置逻辑、历史查询 API。改动最大。
- **llm_platform 模块**（`src/modules/llm_platform/`）：新增 LLMCallLog 模型与 Repository，在 LLM 调用层统一拦截记录。
- **shared 模块**（`src/shared/`）：新增 ExecutionContext（contextvars）、ExternalAPICallLog 模型与通用日志工具。
- **Research 模块**（`src/modules/research/`）：五个专家的 Agent prompt、DTO、output_parser 改造；外部 API adapter 接入调用日志。
- **Debate 模块**（`src/modules/debate/`）：Bull/Bear/Resolution 三个 Agent 同上改造。
- **Judge 模块**（`src/modules/judge/`）：Verdict Agent 同上改造。
- **数据库**：新增 Alembic 迁移（research_sessions、node_executions、llm_call_logs、external_api_call_logs 四张表）。
- **API**：新增历史查询端点；现有 `POST /research` 响应扩展（附带 session_id）。
- **依赖**：无新外部依赖，复用现有 SQLAlchemy + Alembic + Pydantic 栈。
