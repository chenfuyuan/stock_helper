# Spec: research-task-retry

研究任务手动重试能力：通过 REST API 对已有 `partial`/`failed` 状态的 ResearchSession 发起重试，仅重新执行失败的专家节点，复用已成功专家的 result_data，重新执行聚合/辩论/裁决，产出完整研究结论。每次重试创建独立子 session（关联 parent_session_id），保留完整审计链。

**测试约定**：每个 `#### Scenario:` 在变更交付时须对应至少一个自动化测试用例（单元或集成）；实现顺序可先实现再补测，以完整测试通过为需求完成标准。

---

## Requirements

### Requirement: REST 端点 — POST /api/v1/coordinator/research/{session_id}/retry

Coordinator 模块 SHALL 暴露 `POST /api/v1/coordinator/research/{session_id}/retry` REST 端点，位于 `src/modules/coordinator/presentation/rest/` 下。

请求体 SHALL 为 JSON，包含以下可选字段：
- `skip_debate`（bool，可选，默认 `false`）：若为 `true`，重试时跳过辩论和裁决阶段。

路径参数 `session_id` SHALL 为 UUID 格式。

响应体 SHALL 与 `POST /api/v1/coordinator/research` 的 `ResearchOrchestrationResponse` 结构一致（含 symbol、overall_status、expert_results、debate_outcome、verdict、session_id、retry_count）。响应中的 `session_id` SHALL 为新创建的子 session ID。

路由 SHALL 处理以下异常并返回对应 HTTP 状态码：
- session_id 不存在 → 404
- session 状态为 `completed`（无需重试）→ 400
- session 状态为 `running`（正在执行中）→ 409
- 重试后全部专家仍失败 → 500
- 其他未预期异常 → 500（记录日志）

#### Scenario: 对 partial session 发起重试成功

- **WHEN** 用户对状态为 `partial` 的 session 发起重试请求，且存在 2 个失败专家
- **THEN** 系统创建新的子 session（parent_session_id 指向源 session，retry_count=源 session retry_count+1），仅重新执行失败的 2 个专家，复用成功的 3 个专家结果，重新执行聚合/辩论/裁决，返回完整研究结果

#### Scenario: 对 failed session 发起重试成功

- **WHEN** 用户对状态为 `failed` 的 session 发起重试请求
- **THEN** 系统重新执行所有专家节点，返回完整研究结果

#### Scenario: session_id 不存在返回 404

- **WHEN** 用户使用不存在的 session_id 发起重试请求
- **THEN** 系统返回 HTTP 404，响应体包含可区分的错误信息

#### Scenario: session 状态为 completed 返回 400

- **WHEN** 用户对状态为 `completed` 的 session 发起重试请求
- **THEN** 系统返回 HTTP 400，响应体包含"该研究会话已完成，无需重试"的错误信息

#### Scenario: session 状态为 running 返回 409

- **WHEN** 用户对状态为 `running` 的 session 发起重试请求
- **THEN** 系统返回 HTTP 409，响应体包含"该研究会话正在执行中，请等待完成后再重试"的错误信息

#### Scenario: 重试后全部专家仍失败返回 500

- **WHEN** 重试执行后所有专家节点均失败
- **THEN** 系统返回 HTTP 500，响应体包含"重试后全部专家仍执行失败，请检查数据或稍后重试"的错误信息

#### Scenario: skip_debate 为 true 时跳过辩论和裁决

- **WHEN** 重试请求体包含 `"skip_debate": true`
- **THEN** 系统在重试时跳过辩论和裁决阶段，响应体中 `debate_outcome` 和 `verdict` 均为 `null`

#### Scenario: 重试响应包含正确的 retry_count

- **WHEN** 源 session 的 `retry_count` 为 `1`，用户发起重试
- **THEN** 响应体中的 `retry_count` 为 `2`，新创建的子 session 的 `retry_count` 也为 `2`

#### Scenario: 重试响应包含新的 session_id

- **WHEN** 用户对 session 发起重试请求
- **THEN** 响应体中的 `session_id` 为新创建的子 session ID，与源 session ID 不同

### Requirement: 重试逻辑实现

Application 层 SHALL 实现 `ResearchOrchestrationService.retry(session_id: UUID, skip_debate: bool = False) -> ResearchResult` 方法，实现以下逻辑：
1. 查询源 session，校验存在性及状态（非 completed、非 running）
2. 查询该 session 的所有 NodeExecution 记录
3. 按 node_type 分离成功专家（status=success 且 result_data 不为 null）和失败专家（status=failed）
4. 构建新的 ResearchRequest：experts=失败专家列表，pre_populated_results=成功专家结果，parent_session_id=源 session ID，retry_count=源 session retry_count+1
5. 委托给编排器执行，返回完整结果

#### Scenario: 正确分离成功和失败专家

- **WHEN** 源 session 有 3 个成功专家、2 个失败专家
- **THEN** 重试请求的 experts 包含 2 个失败专家，pre_populated_results 包含 3 个成功专家的结果

#### Scenario: 没有失败专家时拒绝重试

- **WHEN** 源 session 所有专家都成功（status=completed）
- **THEN** 系统抛出 `SessionNotRetryableError`，返回 HTTP 400

#### Scenario: 复用成功专家结果

- **WHEN** 重试执行时
- **THEN** 成功专家的结果直接从 pre_populated_results 获取，不重新执行对应专家节点

### Requirement: 编排器支持预填充结果

`LangGraphResearchOrchestrator.run()` 方法 SHALL 支持读取 `request.pre_populated_results`，非 None 时将其注入到图的初始状态 `initial_state["results"]`，使这些专家结果在聚合阶段可用。

#### Scenario: 预填充结果注入图状态

- **WHEN** `request.pre_populated_results` 包含 `{"technical_analyst": {...}, "financial_auditor": {...}}`
- **THEN** 图的初始状态 `results` 字段包含这些预填充结果，仅执行未在 pre_populated_results 中的专家

#### Scenario: pre_populated_results 为 None 时行为不变

- **WHEN** `request.pre_populated_results` 为 `None`
- **THEN** 编排器行为与修改前一致，正常执行所有请求的专家
