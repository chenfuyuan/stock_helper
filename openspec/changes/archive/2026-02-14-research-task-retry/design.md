## Context

当前 Coordinator 编排流水线（`LangGraphResearchOrchestrator.run()`）是一次性执行：创建 `ResearchSession` → 并行调用专家 → 聚合 → 辩论 → 裁决 → 更新 session 状态。单个专家失败时记录到 `errors` 并降级为 `partial`/`failed`，不提供任何重试路径。

已有的持久化基础设施：
- `ResearchSession`：记录每次研究的 symbol、selected_experts、options、status、created_at 等。
- `NodeExecution`：记录每个节点的 result_data（成功时的完整结果）和 error 信息（失败时）。
- `IResearchSessionRepository`：提供 `get_session_by_id()` 和 `get_node_executions_by_session()` 查询能力。

这意味着重试所需的"已成功专家结果"和"失败专家列表"已经持久化在数据库中，可以直接查询复用。

## Goals / Non-Goals

**Goals:**
- 提供 REST API 端点，允许用户对 `partial`/`failed` 状态的 session 发起重试
- 仅重新执行失败的专家节点，复用已成功的专家 result_data
- 合并新旧结果后重新执行聚合 → 辩论 → 裁决，产出完整研究结论
- 新建一个子 session 记录重试执行（关联 parent_session_id），保留完整审计链
- 重试可多次调用，每次仍只跑"仍然失败"的专家

**Non-Goals:**
- 不做编排内自动重试（不修改 LangGraph 图结构）
- 不做跨 session 的结果合并（每次重试基于单一 parent session）
- 不限制最大重试次数（由调用方自行控制）
- 不处理辩论/裁决节点的单独重试（仅重试专家节点，辩论/裁决始终重新执行）

## Decisions

### Decision 1：重试产生新 session 而非原地更新

**选择**：每次重试创建一条新的 `ResearchSession`（带 `parent_session_id` 指向源 session），而非修改原 session 的状态和结果。

**理由**：
- 保留完整审计链——每次执行（含重试）都有独立的 NodeExecution 记录和时间线
- 原 session 的历史数据不被覆盖，便于问题排查
- 与现有 `GET /research/sessions/{id}` 查询逻辑兼容，无需改动查询行为

**替代方案**：原地更新 session 状态和 results → 丢失历史记录，且与 NodeExecution 的 session_id 关联逻辑冲突。

### Decision 2：重试流程复用现有编排器

**选择**：在 `LangGraphResearchOrchestrator` 中扩展 `run()` 方法（或新增 `run_retry()`），支持传入 `pre_populated_results`（已成功的专家结果 dict）。图执行时仅 fan-out 到失败的专家，聚合阶段合并 pre_populated_results 与新结果。

**理由**：
- 复用现有图结构和节点逻辑，改动最小
- `route_to_experts` 已支持按 `selected_experts` 动态路由，只需传入失败的专家子集即可
- 聚合节点只需额外合并 pre_populated_results

**替代方案**：构建独立的重试专用图 → 代码重复，维护两套图结构成本高。

### Decision 3：重试入口放在 Application 层

**选择**：在 `ResearchOrchestrationService` 中新增 `retry()` 方法（或新建 `RetryResearchService`），负责：
1. 查询原 session 及其 NodeExecution 记录
2. 分离成功/失败专家
3. 构建重试 `ResearchRequest`（仅包含失败专家 + 已成功结果）
4. 委托 `IResearchOrchestrationPort` 执行

**理由**：重试的"查数据库 → 分析失败原因 → 决定重跑哪些"是应用层编排逻辑，不属于领域模型也不属于基础设施。保持 Application 层薄编排的职责定位。

**决定**：在现有 `ResearchOrchestrationService` 中新增 `retry(session_id)` 方法，不单独建 Service，因为重试与首次执行共享同一个 Port 和相同的后处理逻辑。

### Decision 4：IResearchOrchestrationPort 接口扩展

**选择**：`ResearchRequest` DTO 新增可选字段 `pre_populated_results: dict[str, Any] | None = None`，编排器收到后将其注入图初始状态。`route_to_experts` 仍按 `selected_experts`（此时仅含失败专家）路由。聚合节点在 `results` 中已包含 pre_populated_results（通过图初始状态注入），无需修改聚合逻辑。

**理由**：
- 对 Port 接口改动最小（仅 DTO 加一个可选字段）
- 编排器实现（LangGraph）的改动也很小——仅在 `initial_state["results"]` 中预填充已有结果
- `merge_dicts` reducer 天然支持合并预填充结果与新专家结果

### Decision 5：Session 模型扩展策略

**选择**：
- `ResearchSession` 新增 `retry_count: int = 0`（该 session 被重试的次数，初次执行为 0）和 `parent_session_id: UUID | None = None`（重试时指向源 session）
- ORM 模型 `ResearchSessionModel` 对应新增两列
- Alembic migration 添加列（`retry_count` INT DEFAULT 0, `parent_session_id` UUID NULLABLE + FK）

**理由**：`retry_count` 方便前端展示"已重试几次"；`parent_session_id` 支持链式追溯。

### Decision 6：重试 API 端点设计

```
POST /api/v1/coordinator/research/{session_id}/retry
```

- 请求体：可选 `skip_debate: bool = false`（与原接口一致）
- 校验：session 必须存在，状态必须为 `partial` 或 `failed`
- 响应：与 `POST /research` 相同的 `ResearchOrchestrationResponse`（含新 session_id）
- 错误码：404（session 不存在）、400（session 已是 completed 状态无需重试）、500（重试执行失败）

## Risks / Trade-offs

- **[风险] 源 session 成功专家的 result_data 格式可能随版本变化** → 短期内专家返回格式稳定；长期可在重试时校验 result_data schema，不兼容时降级为全量重跑。
- **[风险] 高并发下对同一 session 多次触发重试** → 每次重试创建独立子 session，互不影响；前端可通过轮询 session 状态防止重复触发。
- **[Trade-off] 辩论和裁决始终重新执行，即使原 session 中辩论已成功** → 辩论/裁决结果依赖专家结果的完整性，部分专家结果变化后必须重新辩论才有意义。token 开销可接受（辩论/裁决远轻于专家分析）。
- **[Trade-off] pre_populated_results 作为 ResearchRequest 可选字段，稍增 DTO 复杂度** → 相比新建独立 Port 方法，改动最小且保持接口一致性。
