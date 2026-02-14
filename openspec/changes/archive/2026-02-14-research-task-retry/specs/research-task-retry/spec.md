# Spec: research-task-retry

研究任务手动重试能力：通过 REST API 对已有 `partial`/`failed` 状态的 ResearchSession 发起重试，仅重新执行失败的专家节点，复用已成功专家的 result_data，重新执行聚合/辩论/裁决，产出完整研究结论。每次重试创建独立子 session（关联 parent_session_id），保留完整审计链。

**测试约定**：每个 `#### Scenario:` 在变更交付时须对应至少一个自动化测试用例（单元或集成）；实现顺序可先实现再补测，以完整测试通过为需求完成标准。

---

## ADDED Requirements

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

- **WHEN** 用户对一个 `partial` 状态的 session（3 个专家成功、2 个失败）发起 `POST /research/{session_id}/retry`
- **THEN** 系统 SHALL 仅重新执行 2 个失败的专家，复用 3 个已成功的结果，返回 HTTP 200，`overall_status` 为 `"completed"`（假设重试全部成功），`expert_results` 包含全部 5 个专家的结果

#### Scenario: 对 failed session 发起重试成功

- **WHEN** 用户对一个 `failed` 状态的 session（全部专家失败）发起重试
- **THEN** 系统 SHALL 重新执行全部失败的专家，返回 HTTP 200，响应包含重试后的完整结果

#### Scenario: 对 completed session 发起重试返回 400

- **WHEN** 用户对一个 `completed` 状态的 session 发起重试
- **THEN** 系统 SHALL 返回 HTTP 400，响应体包含"该 session 已完成，无需重试"的错误信息

#### Scenario: 对 running session 发起重试返回 409

- **WHEN** 用户对一个 `running` 状态的 session 发起重试
- **THEN** 系统 SHALL 返回 HTTP 409，响应体包含"该 session 正在执行中，请等待完成后再重试"的错误信息

#### Scenario: session 不存在时返回 404

- **WHEN** 用户对一个不存在的 session_id 发起重试
- **THEN** 系统 SHALL 返回 HTTP 404

#### Scenario: 重试时 skip_debate 为 true

- **WHEN** 用户对 partial session 发起重试，请求体含 `"skip_debate": true`
- **THEN** 系统 SHALL 重新执行失败专家并跳过辩论和裁决阶段，响应中 `debate_outcome` 和 `verdict` 均为 `null`

---

### Requirement: 重试仅执行失败的专家节点

重试 SHALL 从原 session 的 NodeExecution 记录中识别失败的专家节点（status="failed" 的专家类型节点），仅对这些专家重新执行。已成功专家的 `result_data` SHALL 从 NodeExecution 记录中读取并复用，不重新调用。

辩论（debate）和裁决（judge）节点 SHALL 始终重新执行（因其结果依赖专家结果的完整性）。

#### Scenario: 复用已成功专家的结果

- **WHEN** 原 session 中 technical_analyst 成功（result_data 存在）、macro_intelligence 失败
- **THEN** 重试 SHALL 直接使用 technical_analyst 的历史 result_data，仅调用 macro_intelligence 的 `run_expert()`

#### Scenario: 辩论和裁决始终重新执行

- **WHEN** 原 session 中辩论已成功但有专家失败，用户发起重试
- **THEN** 系统 SHALL 在专家补跑完成后重新执行辩论和裁决，而非复用原辩论结果

#### Scenario: 重试后部分专家仍失败

- **WHEN** 重试时 2 个失败专家中 1 个恢复成功、1 个仍然失败
- **THEN** 新 session 的 `overall_status` SHALL 为 `"partial"`，成功的专家（含复用的 + 新成功的）正常返回 data，仍失败的专家标记 `status: "failed"` 含 error

---

### Requirement: 重试创建子 session

每次重试 SHALL 创建一个新的 `ResearchSession`，该子 session 的 `parent_session_id` SHALL 指向被重试的源 session ID。子 session 的 `retry_count` SHALL 为源 session 的 `retry_count + 1`。

子 session 的其余字段（symbol、selected_experts、options、trigger_source）SHALL 继承自源 session。`selected_experts` SHALL 记录本次实际执行的专家列表（仅失败的专家子集）。

#### Scenario: 子 session 关联源 session

- **WHEN** 用户对 session A 发起重试
- **THEN** 系统 SHALL 创建 session B，`B.parent_session_id = A.id`，`B.retry_count = A.retry_count + 1`

#### Scenario: 多次重试形成链式关系

- **WHEN** 用户对 session A 重试得到 session B（仍 partial），再对 B 重试得到 session C
- **THEN** `C.parent_session_id = B.id`，`C.retry_count = 2`

#### Scenario: 子 session 的 selected_experts 为失败专家子集

- **WHEN** 源 session 选中 5 个专家，其中 2 个失败
- **THEN** 子 session 的 `selected_experts` SHALL 仅包含 2 个失败专家的类型值

---

### Requirement: Application 层重试用例

`ResearchOrchestrationService` SHALL 新增 `retry(session_id: UUID, skip_debate: bool = False) -> ResearchResult` 方法，负责：

1. 通过 `IResearchSessionRepository` 查询源 session，校验状态为 `partial` 或 `failed`。
2. 查询源 session 的 NodeExecution 记录，分离成功/失败的专家。
3. 从成功专家的 NodeExecution 中提取 `result_data` 作为 `pre_populated_results`。
4. 构建 `ResearchRequest`（experts 仅含失败专家，附加 `pre_populated_results`）。
5. 委托 `IResearchOrchestrationPort.run()` 执行。
6. 返回 `ResearchResult`。

session 不存在时 SHALL 抛出领域异常（由 Presentation 层映射为 404）。session 状态为 `completed` 时 SHALL 抛出校验异常（映射为 400）。session 状态为 `running` 时 SHALL 抛出校验异常（映射为 409）。

#### Scenario: session 不存在时抛异常

- **WHEN** 调用 `retry()` 时 session_id 不存在
- **THEN** SHALL 抛出领域异常，不调用编排 Port

#### Scenario: session 状态为 completed 时拒绝重试

- **WHEN** 调用 `retry()` 时 session 状态为 `completed`
- **THEN** SHALL 抛出校验异常，不调用编排 Port

#### Scenario: session 状态为 running 时拒绝重试

- **WHEN** 调用 `retry()` 时 session 状态为 `running`
- **THEN** SHALL 抛出校验异常，不调用编排 Port

#### Scenario: 正确分离成功与失败专家

- **WHEN** 源 session 有 5 个专家的 NodeExecution 记录，其中 3 个 status="success"、2 个 status="failed"
- **THEN** `retry()` SHALL 构建 ResearchRequest.experts 仅含 2 个失败专家，`pre_populated_results` 含 3 个成功专家的 result_data

---

### Requirement: ResearchRequest DTO 扩展

`ResearchRequest`（位于 `src/modules/coordinator/domain/dtos/research_dtos.py`）SHALL 新增可选字段：

- `pre_populated_results: dict[str, Any] | None = None`：重试时传入已成功专家的结果，key 为专家类型 value（如 `"technical_analyst"`），value 为该专家的 result_data dict。
- `parent_session_id: UUID | None = None`：重试时关联的源 session ID。
- `retry_count: int = 0`：本次执行的重试计数。

首次研究请求中这些字段 SHALL 保持默认值（None / 0），对现有行为无影响。

#### Scenario: 首次请求不含 pre_populated_results

- **WHEN** 首次发起研究请求，不传 pre_populated_results
- **THEN** 编排行为与改动前完全一致，所有专家均被执行

#### Scenario: 重试请求包含 pre_populated_results

- **WHEN** 重试时 ResearchRequest 含 `pre_populated_results={"technical_analyst": {...}, "financial_auditor": {...}}`，`experts=["macro_intelligence"]`
- **THEN** 编排器 SHALL 仅执行 macro_intelligence，聚合时合并 pre_populated_results 中的结果

---

### Requirement: 编排器支持 pre_populated_results

`LangGraphResearchOrchestrator.run()`（位于 `src/modules/coordinator/infrastructure/orchestration/langgraph_orchestrator.py`）SHALL 在构建图初始状态时，将 `request.pre_populated_results` 注入 `initial_state["results"]`。

当 `pre_populated_results` 不为 None 时：
- `initial_state["results"]` SHALL 预填充为 `pre_populated_results` 的内容。
- `route_to_experts` 仍按 `selected_experts`（仅失败专家）路由，不受 pre_populated_results 影响。
- 聚合节点读取的 `results` dict 中 SHALL 同时包含预填充的成功结果和新执行的专家结果。

当 `pre_populated_results` 为 None 时，行为与改动前一致（`initial_state["results"]` 为空 dict）。

子 session 的创建 SHALL 使用 `request.parent_session_id` 和 `request.retry_count`。

#### Scenario: pre_populated_results 注入图初始状态

- **WHEN** `request.pre_populated_results = {"technical_analyst": {"signal": "BULLISH", ...}}`
- **THEN** `initial_state["results"]` SHALL 为 `{"technical_analyst": {"signal": "BULLISH", ...}}`

#### Scenario: merge_dicts reducer 合并预填充与新结果

- **WHEN** initial_state 预填充了 technical_analyst 结果，macro_intelligence 节点执行成功返回新结果
- **THEN** 聚合节点看到的 `results` SHALL 包含 technical_analyst 和 macro_intelligence 两个 key

#### Scenario: pre_populated_results 为 None 时无影响

- **WHEN** `request.pre_populated_results` 为 None
- **THEN** `initial_state["results"]` 为空 dict，与改动前行为一致

---

### Requirement: ResearchResult DTO 包含 retry_count

`ResearchResult`（位于 `src/modules/coordinator/domain/dtos/research_dtos.py`）SHALL 包含 `retry_count: int = 0` 字段，表示本次研究的重试计数（首次执行为 0，首次重试为 1，以此类推）。

#### Scenario: 首次执行 retry_count 为 0

- **WHEN** 首次执行研究编排完成
- **THEN** `ResearchResult.retry_count` SHALL 为 `0`

#### Scenario: 重试执行 retry_count 递增

- **WHEN** 对 retry_count=0 的 session 重试完成
- **THEN** `ResearchResult.retry_count` SHALL 为 `1`
