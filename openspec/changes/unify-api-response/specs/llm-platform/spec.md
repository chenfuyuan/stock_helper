## MODIFIED Requirements

### Requirement: Web 搜索响应格式
Web 搜索接口 SHALL 返回统一的 `BaseResponse[WebSearchApiResponse]` 格式，确保与其他 API 接口响应格式的一致性。

#### Scenario: 成功的 Web 搜索响应
- **WHEN** Web 搜索请求成功完成
- **THEN** 系统返回 `BaseResponse[WebSearchApiResponse]`，其中：
  - `success: true`
  - `message: "Web 搜索成功完成"`
  - `code: "WEB_SEARCH_SUCCESS"`
  - `data: WebSearchApiResponse` 包含搜索结果的详细信息

#### Scenario: Web 搜索失败响应
- **WHEN** Web 搜索过程中发生错误
- **THEN** 系统返回 `ErrorResponse`，包含：
  - `success: false`
  - `message: str` 搜索失败的具体描述
  - `code: str` 对应的错误代码（如 "SEARCH_PROVIDER_ERROR"、"QUERY_TOO_LONG" 等）

### Requirement: LLM 聊天响应格式
LLM 聊天接口 SHALL 返回统一的 `BaseResponse[ChatResponse]` 格式，确保响应格式一致性。

#### Scenario: 成功的 LLM 聊天响应
- **WHEN** LLM 聊天请求成功完成
- **THEN** 系统返回 `BaseResponse[ChatResponse]`，其中：
  - `success: true`
  - `message: "LLM 对话成功完成"`
  - `code: "LLM_CHAT_SUCCESS"`
  - `data: ChatResponse` 包含 LLM 生成的回复内容

#### Scenario: LLM 聊天失败响应
- **WHEN** LLM 聊天过程中发生错误
- **THEN** 系统返回 `ErrorResponse`，包含：
  - `success: false`
  - `message: str` LLM 调用失败的具体描述
  - `code: str` 对应的错误代码（如 "LLM_PROVIDER_ERROR"、"MODEL_NOT_AVAILABLE" 等）
