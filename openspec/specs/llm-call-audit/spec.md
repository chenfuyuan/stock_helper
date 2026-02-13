# Spec: llm-call-audit

LLM 调用审计：在 LLMService.generate() 层自动记录每次 LLM 调用的完整信息（prompt、completion、token、耗时、session 关联等），失败时同样记录；持久化不阻塞调用返回；提供按 session_id 查询的 API。

**测试约定**：每个 `#### Scenario:` 在变更交付时须对应至少一个自动化测试用例（单元或集成）；实现顺序可先实现再补测，以完整测试通过为需求完成标准。

---

## Requirements

### Requirement: LLM 调用自动记录

系统 SHALL 在 `LLMService.generate()` 层自动记录每次 LLM 调用的完整信息，无需各调用方模块自行实现。

记录内容 MUST 包含：唯一标识（UUID）、关联 session_id（可为 null）、调用方模块名、调用方 Agent 标识（可为 null）、模型名称、供应商、完整 user prompt、system message、LLM 完整输出、prompt tokens、completion tokens、总 tokens、温度参数、调用耗时（毫秒）、状态（success / failed）、错误信息（失败时）。

#### Scenario: 研究流水线中的 LLM 调用

- **WHEN** 技术分析师 Agent 在研究流水线中调用 LLM 生成分析
- **THEN** 系统自动创建一条 `LLMCallLog`，包含完整 prompt、completion、token 用量、耗时，session_id 关联到当前 ResearchSession

#### Scenario: 非研究流水线的 LLM 调用

- **WHEN** 某模块在非研究流水线上下文中调用 LLM（无 ExecutionContext）
- **THEN** 系统仍创建 `LLMCallLog`，但 session_id 为 null

### Requirement: LLM 调用失败记录

系统 SHALL 在 LLM 调用失败（异常、超时等）时同样记录日志，status 为 `failed`，error_message 包含异常信息。completion_text 在失败时可为 null。

#### Scenario: LLM 调用超时

- **WHEN** LLM 调用因网络超时抛出异常
- **THEN** 系统创建一条 `LLMCallLog`，status=failed，error_message 包含超时异常信息，completion_text 为 null，latency_ms 反映实际等待时间

#### Scenario: LLM 返回格式错误

- **WHEN** LLM 调用成功返回但返回内容无法解析
- **THEN** LLM 调用层面的 `LLMCallLog` status=success（因为 LLM 确实返回了结果），completion_text 包含原始返回内容；解析失败由上层 Agent 处理

### Requirement: 审计日志写入不阻塞 LLM 调用

`LLMCallLog` 的持久化 SHALL NOT 阻塞 LLM 调用的返回。写入失败时 MUST 记录 warning 级别日志，LLM 调用结果正常返回给调用方。

#### Scenario: 审计写入失败

- **WHEN** LLM 调用成功，但审计日志写入数据库失败
- **THEN** LLM 调用结果正常返回给调用方，日志中记录审计写入失败的 warning

### Requirement: 按 session 查询 LLM 调用日志

系统 SHALL 提供通过 session_id 查询关联 LLM 调用日志的能力（供 Coordinator 历史查询 API 聚合使用）。

`GET /research/sessions/{session_id}/llm-calls` 端点 SHALL 返回该 session 关联的所有 LLM 调用记录，按 created_at 排序。

#### Scenario: 查询某次研究的 LLM 调用

- **WHEN** 客户端请求 `GET /research/sessions/{session_id}/llm-calls`
- **THEN** 返回该 session 下所有 LLM 调用记录列表，每条包含 caller_agent、model_name、prompt_text、completion_text、total_tokens、latency_ms、status

#### Scenario: 无关联调用

- **WHEN** 查询一个没有 LLM 调用记录的 session_id
- **THEN** 返回空列表，HTTP 200
