# Spec: pipeline-execution-tracking

研究流水线执行跟踪：ResearchSession 与 NodeExecution 的生命周期管理、持久化及历史查询 API。Coordinator 在每次研究启动时创建会话记录，在节点执行时记录 NodeExecution，流水线结束后更新会话状态；提供 GET /research/sessions 与 GET /research/sessions/{session_id} 等查询能力。

**测试约定**：每个 `#### Scenario:` 在变更交付时须对应至少一个自动化测试用例（单元或集成）；实现顺序可先实现再补测，以完整测试通过为需求完成标准。

---

## Requirements

### Requirement: ResearchSession 生命周期管理

系统 SHALL 在每次研究流水线启动时创建一个 `ResearchSession` 记录，并在流水线结束后更新其最终状态。

`ResearchSession` 包含以下信息：唯一标识（UUID）、股票代码（symbol）、执行状态（running / completed / partial / failed）、选中的专家列表、执行选项、触发来源、创建时间、完成时间、总耗时（毫秒）、重试计数（`retry_count`，int，默认 0）、父会话标识（`parent_session_id`，UUID，可为 null）。

- 流水线启动时，状态 MUST 设为 `running`。
- 所有节点成功完成时，状态 MUST 更新为 `completed`。
- 部分节点成功、部分失败时，状态 MUST 更新为 `partial`。
- 所有节点均失败时，状态 MUST 更新为 `failed`。
- `completed_at` 和 `duration_ms` MUST 在流水线结束后写入。
- 首次执行时，`retry_count` MUST 为 `0`，`parent_session_id` MUST 为 `null`。
- 重试执行时，`retry_count` MUST 为源 session 的 `retry_count + 1`，`parent_session_id` MUST 指向被重试的源 session ID。

#### Scenario: 完整成功的研究流水线

- **WHEN** 用户发起一次研究请求，选择全部 5 个专家且不跳过辩论
- **THEN** 系统创建一个 `ResearchSession`（status=running），流水线全部节点执行成功后更新 status=completed，completed_at 和 duration_ms 均不为 null

#### Scenario: 部分专家失败

- **WHEN** 用户发起研究请求，其中 2 个专家执行失败、3 个成功，辩论和裁决正常完成
- **THEN** `ResearchSession` 最终 status=partial

#### Scenario: 全部失败

- **WHEN** 用户发起研究请求，所有专家均执行失败
- **THEN** `ResearchSession` 最终 status=failed，completed_at 和 duration_ms 仍被记录

#### Scenario: 首次执行的 session 字段

- **WHEN** 用户首次发起研究请求
- **THEN** 创建的 `ResearchSession` 中 `retry_count` 为 `0`，`parent_session_id` 为 `null`

#### Scenario: 重试执行的 session 字段

- **WHEN** 用户对已有 session 发起重试，源 session 的 `retry_count` 为 `1`
- **THEN** 新创建的子 session 中 `retry_count` 为 `2`，`parent_session_id` 指向源 session ID

### Requirement: NodeExecution 成功记录

系统 SHALL 在每个 LangGraph 节点执行成功后，创建一个 `NodeExecution` 记录，包含：唯一标识、关联 session_id、节点类型（technical_analyst / financial_auditor / valuation_modeler / macro_intelligence / catalyst_detective / debate / judge）、状态（success）、结构化业务结果（JSONB）、叙述性报告（TEXT）、开始时间、结束时间、耗时。

#### Scenario: 专家节点成功

- **WHEN** 技术分析师专家节点执行成功，返回结构化 JSON 结果和叙述性报告
- **THEN** 系统创建一个 `NodeExecution`，status=success，result_data 包含完整结构化结果，narrative_report 包含文字报告，error_type 和 error_message 为 null

#### Scenario: Debate 节点成功

- **WHEN** Debate 节点（含 Bull/Bear/Resolution）执行成功
- **THEN** 系统创建一个 node_type=debate 的 `NodeExecution`，result_data 包含完整辩论结果

### Requirement: NodeExecution 失败记录

系统 SHALL 在每个 LangGraph 节点执行失败后，同样创建一个 `NodeExecution` 记录，状态设为 `failed`，并记录 error_type（异常类名）和 error_message（错误详情）。result_data 和 narrative_report 在失败时可为 null。

#### Scenario: 专家节点抛出异常

- **WHEN** 财务审计员专家节点执行过程中抛出 `LLMOutputParseError` 异常
- **THEN** 系统创建一个 `NodeExecution`，status=failed，error_type="LLMOutputParseError"，error_message 包含异常详情，result_data 为 null

#### Scenario: 节点超时

- **WHEN** 某专家节点因 LLM 调用超时而失败
- **THEN** 系统创建一个 `NodeExecution`，status=failed，error_type 和 error_message 反映超时原因

### Requirement: 持久化不阻塞主流程

NodeExecution 的持久化写入失败 SHALL NOT 导致研究流水线主流程中断。写入失败时系统 MUST 记录 error 级别日志，但节点结果正常返回给下游。

#### Scenario: 数据库写入失败

- **WHEN** 专家节点执行成功，但 NodeExecution 写入数据库时发生连接超时
- **THEN** 研究流水线继续正常执行后续节点，日志中记录持久化失败的 error 信息

### Requirement: 历史会话列表查询

系统 SHALL 提供 `GET /research/sessions` 端点，返回历史研究会话列表，支持分页和筛选。

- 支持按 `symbol` 精确筛选
- 支持按时间范围（`start_date` / `end_date`）筛选
- 返回结果按 `created_at` 降序排列
- 支持 `page` 和 `page_size` 分页参数

#### Scenario: 按股票代码查询

- **WHEN** 客户端请求 `GET /research/sessions?symbol=000001.SZ`
- **THEN** 返回该股票的所有历史研究会话列表，包含 id、symbol、status、created_at、duration_ms 等摘要信息

#### Scenario: 空结果

- **WHEN** 客户端请求一个从未研究过的股票代码
- **THEN** 返回空列表，HTTP 200

### Requirement: 会话详情查询

系统 SHALL 提供 `GET /research/sessions/{session_id}` 端点，返回指定会话的完整信息及其所有 NodeExecution 记录。

#### Scenario: 查询存在的会话

- **WHEN** 客户端请求 `GET /research/sessions/{valid_session_id}`
- **THEN** 返回会话基本信息 + 所有 NodeExecution 列表（按 started_at 排序），每个 NodeExecution 包含 node_type、status、result_data、narrative_report、error_type、error_message、duration_ms

#### Scenario: 查询不存在的会话

- **WHEN** 客户端请求 `GET /research/sessions/{invalid_id}`
- **THEN** 返回 HTTP 404

### Requirement: 现有 POST /research 响应扩展

现有 `POST /research` 端点的响应 SHALL 新增 `session_id` 字段，返回本次研究会话的唯一标识，便于客户端后续查询详情。

#### Scenario: 研究请求返回 session_id

- **WHEN** 客户端发起 `POST /research` 并成功执行
- **THEN** 响应体中包含 `session_id` 字段（UUID 格式），可用于 `GET /research/sessions/{session_id}` 查询
