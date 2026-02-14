## Why

当前研究编排流水线中，单个专家节点失败后仅记录错误并降级（`partial` / `failed`），不会重试。实际运行中，专家失败多由瞬时问题导致（LLM 超时、API 限流、网络抖动等），简单重试即可恢复。现状导致：

1. **研究结果不完整**：partial 结果缺少关键专家观点，影响后续辩论与裁决质量。
2. **人工干预成本高**：用户只能手动重新发起整个研究请求，浪费已成功专家的执行时间和 token 费用。

需要提供手动重试 API，仅对已有 session 中失败的专家补跑，复用已成功的结果，最大程度节省 token 开销。不做编排内自动重试——何时重试由用户决定，避免 LLM 持续不可用时白白消耗资源。

## What Changes

- **重试 API 端点**：新增 `POST /api/v1/coordinator/research/{session_id}/retry`，读取指定 session 中失败的专家列表，仅对失败专家重新执行，复用已成功的专家结果，重新执行聚合/辩论/裁决，返回完整的研究结果。
- **Session 模型扩展**：`ResearchSession` 新增 `retry_count`（累计重试次数）和 `parent_session_id`（关联原 session）字段，支持重试链路追溯。

## Capabilities

### New Capabilities
- `research-task-retry`：研究任务手动重试能力——通过 API 对已有 session 中失败的专家补跑，复用成功结果，重新聚合/辩论/裁决。

### Modified Capabilities
- `coordinator-research-orchestration`：响应契约扩展（新增 `retry_count` 字段）。
- `pipeline-execution-tracking`：ResearchSession 模型新增 `retry_count` / `parent_session_id` 字段；NodeExecution 记录标识来源 session 以支持重试链路追溯。

## Impact

- **代码**：`src/modules/coordinator/` — langgraph_orchestrator（支持传入已有 results 启动编排）、research_routes（新端点）、research_session（模型扩展）、research_dtos（DTO 扩展）、application 层新增 RetryResearchService 或在现有 service 中扩展重试用例
- **API**：POST /research 响应体新增 `retry_count` 字段；新增 POST /research/{session_id}/retry 端点
- **数据库**：research_sessions 表新增 `retry_count`（int, default 0）/ `parent_session_id`（UUID nullable）列（需 Alembic migration）
- **依赖**：无新外部依赖
