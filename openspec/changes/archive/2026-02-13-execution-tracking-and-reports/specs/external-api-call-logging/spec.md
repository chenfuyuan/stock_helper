## ADDED Requirements

### Requirement: 外部 API 调用自动记录

系统 SHALL 在 `WebSearchService.search()` 层自动记录每次外部 API 调用的完整信息。

记录内容 MUST 包含：唯一标识（UUID）、关联 session_id（可为 null）、服务名（如 bochai）、操作名（如 web-search）、请求参数（JSONB）、完整响应数据（TEXT）、HTTP 状态码、调用耗时（毫秒）、状态（success / failed）、错误信息（失败时）。

#### Scenario: 博查搜索成功

- **WHEN** 宏观情报员 Agent 通过 WebSearchService 调用博查搜索宏观经济数据
- **THEN** 系统自动创建一条 `ExternalAPICallLog`，service_name=bochai，operation=web-search，request_params 包含搜索 query 等参数，response_data 包含完整搜索结果，session_id 关联到当前 ResearchSession

#### Scenario: 无上下文的外部 API 调用

- **WHEN** 某模块在非研究流水线上下文中调用外部 API
- **THEN** 系统仍创建 `ExternalAPICallLog`，但 session_id 为 null

### Requirement: 外部 API 调用失败记录

系统 SHALL 在外部 API 调用失败（网络异常、非 2xx 响应等）时记录日志，status 为 `failed`，error_message 包含异常信息。

#### Scenario: 博查 API 返回 500

- **WHEN** 博查搜索 API 返回 HTTP 500 错误
- **THEN** 系统创建一条 `ExternalAPICallLog`，status=failed，status_code=500，error_message 包含错误详情

#### Scenario: 网络连接失败

- **WHEN** 博查搜索因网络不可达而失败
- **THEN** 系统创建一条 `ExternalAPICallLog`，status=failed，error_message 包含连接异常信息，status_code 为 null

### Requirement: 日志写入不阻塞 API 调用

`ExternalAPICallLog` 的持久化 SHALL NOT 阻塞外部 API 调用的返回。写入失败时 MUST 记录 warning 级别日志。

#### Scenario: 日志写入失败

- **WHEN** 博查搜索成功返回，但日志写入数据库失败
- **THEN** 搜索结果正常返回给调用方，日志中记录写入失败的 warning

### Requirement: 按 session 查询外部 API 调用日志

系统 SHALL 提供 `GET /research/sessions/{session_id}/api-calls` 端点，返回该 session 关联的所有外部 API 调用记录。

#### Scenario: 查询某次研究的 API 调用

- **WHEN** 客户端请求 `GET /research/sessions/{session_id}/api-calls`
- **THEN** 返回该 session 下所有外部 API 调用记录列表，每条包含 service_name、operation、request_params、response_data、latency_ms、status

#### Scenario: 无关联调用

- **WHEN** 查询一个没有外部 API 调用记录的 session_id
- **THEN** 返回空列表，HTTP 200
