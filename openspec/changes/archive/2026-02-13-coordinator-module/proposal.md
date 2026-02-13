## Why

Research 模块的五个专家（技术分析师、财务审计员、估值建模师、宏观情报员、催化剂侦探）已全部实现，但目前只能通过各自独立的 REST 端点逐个调用。系统缺少一个**统一的编排入口**，让用户在一次请求中指定标的与所需专家、并行执行分析、汇总结果。按照愿景中 `Coordinator → Research → Debate → Judge` 的流水线设计，Coordinator 是整条链路的起点和前台，是串联后续 Debate、Judge 模块的前置依赖。

## What Changes

- **新增 Coordinator Bounded Context**（`src/modules/coordinator/`），遵循标准四层结构（Presentation / Application / Domain / Infrastructure）。
- **引入 LangGraph 作为编排引擎**：Coordinator 的研究编排流程使用 LangGraph `StateGraph` 建模为有向图，每个专家为图中一个可选节点，由条件边（conditional edges）根据用户指定的专家列表决定激活哪些节点。LangGraph 作为 Infrastructure 层的实现细节，Domain 和 Application 层不直接依赖 LangGraph API。
- **新增「研究编排」能力**：用户通过单一 REST 端点提交研究请求（symbol + 需要执行的专家列表 + 可选参数），Coordinator 通过 LangGraph 图按需并行调用 Research 模块对应的 Application 服务，汇总结果后统一返回。
- **新增 Domain 模型**：`ResearchTask` 值对象，记录请求元信息（symbol、选定专家列表、各专家可选参数）和汇总结果。当前为请求级生命周期（不持久化），LangGraph 的 checkpointer 机制为后续持久化与断点续跑预留扩展点。
- **新增 REST 端点**：`POST /api/v1/coordinator/research`，接受 `{ symbol, experts, options? }` 请求体。
- **新增依赖**：`langgraph` 包（添加到 `requirements.txt`）。
- **注册路由**：在 `src/api/routes.py` 中挂载 Coordinator 路由。

### 为什么选 LangGraph

1. **有向图建模天然匹配编排场景**：每个专家是一个节点，条件边控制哪些节点被激活，用户指定专家列表即转化为图的路由逻辑。
2. **内置并行支持**：多个无依赖节点可并行执行，无需手写 `asyncio.gather` + 错误收集。
3. **状态管理内聚**：`TypedDict` State 贯穿图执行全过程，天然记录各节点的输入/输出/错误。
4. **可扩展性强**：后续 Debate → Judge 可作为下游节点接入同一图（或子图），实现完整的 `Research → Debate → Judge` 流水线；checkpointer 支持任务持久化与断点恢复。
5. **与 DDD 兼容**：LangGraph 仅作为 Infrastructure 层的编排实现，Domain/Application 层通过 Port 抽象解耦，不感知 LangGraph API。

## Capabilities

### New Capabilities
- `coordinator-research-orchestration`: Coordinator 模块核心能力 —— 基于 LangGraph 的研究编排图，包含：用户指定专家的按需路由、并行执行、结果汇总、单专家失败隔离与优雅降级。涵盖 REST 接口、Application 编排服务、Domain 模型（ResearchTask、ExpertType 枚举、图状态定义）、Infrastructure 层的 LangGraph 图构建与 Research 专家 Adapter。

### Modified Capabilities
（无。Coordinator 通过 Research 模块已有的 Application 接口调用各专家，不改变 Research 的接口契约。）

## Impact

- **新增代码路径**：`src/modules/coordinator/`（application / domain / infrastructure / presentation 四层）。
- **新增依赖**：`langgraph`（添加到 `requirements.txt`）；可能附带 `langchain-core` 作为间接依赖。
- **路由注册**：`src/api/routes.py` 新增 `coordinator_router`。
- **跨模块依赖**：Coordinator → Research（通过 Research 的 Application 服务接口）。Coordinator 不直接依赖 data_engineering 或 llm_platform。
- **测试**：每个 Scenario 须对应自动化测试 —— 正常并行编排、部分专家失败降级、全部失败、入参校验、LangGraph 图路由逻辑等场景。
- **对已有模块无破坏性变更**：Research 模块保持现有接口不变。
