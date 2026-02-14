# Delta Spec: coordinator-research-orchestration

针对研究任务重试能力，对现有 coordinator-research-orchestration 规格的增量变更。

---

## MODIFIED Requirements

### Requirement: 请求体与响应体契约

REST 端点的请求体 SHALL 为 JSON，包含以下字段：
- `symbol`（str，必填）：股票代码
- `experts`（list[str]，必填）：需要执行的专家类型列表，值为 ExpertType 枚举的 value（snake_case），至少 1 个
- `options`（dict[str, dict]，可选）：按专家名提供的专家特有参数。`technical_analyst` 可接受 `analysis_date`（str，ISO 格式日期，默认当天）；`financial_auditor` 可接受 `limit`（int，默认 5）；其他三专家无额外参数。
- `skip_debate`（bool，可选，默认 `false`）：若为 `true`，编排图 SHALL 跳过辩论阶段，行为与修改前一致。

响应体 SHALL 为 JSON，包含以下字段：
- `symbol`（str）：请求的股票代码
- `overall_status`（str）：`"completed"`（全部成功）、`"partial"`（部分成功部分失败）、`"failed"`（全部失败）
- `expert_results`（dict[str, object]）：按专家名分组的结果，每个专家的值包含 `status`（`"success"` 或 `"failed"`）、成功时包含 `data`（该专家的原始分析结果 dict）、失败时包含 `error`（错误信息字符串）
- `debate_outcome`（object | null）：辩论结果。包含 direction、confidence、bull_case、bear_case、risk_matrix、key_disagreements、conflict_resolution。当 `skip_debate=true` 或辩论失败时为 `null`。
- `verdict`（object | null）：裁决结果。包含 action、position_percent、confidence、entry_strategy、stop_loss、take_profit、time_horizon、risk_warnings、reasoning。当 `skip_debate=true`、辩论失败或裁决失败时为 `null`。
- `session_id`（str）：研究会话 ID
- `retry_count`（int）：重试计数，首次执行为 0，每次重试递增 1。

#### Scenario: 首次请求响应包含 retry_count 为 0

- **WHEN** 首次发起 `POST /api/v1/coordinator/research` 研究请求并成功返回
- **THEN** 响应体 SHALL 包含 `retry_count` 字段，值为 `0`

#### Scenario: 重试请求响应包含递增的 retry_count

- **WHEN** 对 partial session 发起重试并成功返回
- **THEN** 响应体 SHALL 包含 `retry_count` 字段，值为源 session 的 retry_count + 1

#### Scenario: 请求含完整字段时正确解析

- **WHEN** 发送请求体 `{"symbol": "000001.SZ", "experts": ["technical_analyst", "macro_intelligence"], "options": {"technical_analyst": {"analysis_date": "2026-02-13"}}}`
- **THEN** 系统 SHALL 正确解析 symbol、experts 列表和专家特有参数，调用对应的专家服务，并执行辩论和裁决阶段

#### Scenario: options 缺失时使用默认值

- **WHEN** 发送请求体不包含 `options` 字段，或 options 中不包含某专家的参数
- **THEN** 系统 SHALL 使用默认值（technical_analyst 默认 analysis_date 为当天，financial_auditor 默认 limit 为 5），正常执行

#### Scenario: 响应体包含 debate_outcome

- **WHEN** 研究编排执行完成且辩论阶段正常完成
- **THEN** 响应体 SHALL 包含 `debate_outcome` 字段，其中包含 direction、confidence、bull_case、bear_case、risk_matrix、key_disagreements、conflict_resolution

#### Scenario: 响应体包含 verdict

- **WHEN** 研究编排执行完成且辩论和裁决阶段均正常完成
- **THEN** 响应体 SHALL 包含 `verdict` 字段，其中包含 action、position_percent、confidence、entry_strategy、stop_loss、take_profit、time_horizon、risk_warnings、reasoning

#### Scenario: skip_debate 为 true 时跳过辩论和裁决

- **WHEN** 请求体包含 `"skip_debate": true`
- **THEN** 系统 SHALL 跳过辩论和裁决阶段，响应体中 `debate_outcome` 和 `verdict` 均为 `null`，其余字段不受影响

#### Scenario: 辩论失败时 debate_outcome 和 verdict 均为 null

- **WHEN** 辩论阶段执行失败（如 LLM 解析错误）
- **THEN** 响应体 `debate_outcome` 和 `verdict` SHALL 均为 `null`，`overall_status` 和 `expert_results` SHALL 不受辩论失败影响

#### Scenario: 辩论成功但裁决失败时 verdict 为 null

- **WHEN** 辩论阶段正常完成但裁决阶段执行失败
- **THEN** 响应体 `debate_outcome` SHALL 正常返回，`verdict` SHALL 为 `null`，`overall_status` 和 `expert_results` SHALL 不受裁决失败影响

#### Scenario: 全部成功时 overall_status 为 completed

- **WHEN** 所有选定专家均执行成功
- **THEN** `overall_status` SHALL 为 `"completed"`，所有 expert_results 中的 status 均为 `"success"`

#### Scenario: 部分成功时 overall_status 为 partial

- **WHEN** 部分选定专家执行成功、部分失败
- **THEN** `overall_status` SHALL 为 `"partial"`，成功的专家 status 为 `"success"` 含 data，失败的专家 status 为 `"failed"` 含 error
