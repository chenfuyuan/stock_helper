## MODIFIED Requirements

### Requirement: 研究编排响应格式
研究编排接口 SHALL 返回统一的 `BaseResponse[ResearchOrchestrationResponse]` 格式，确保与其他 API 接口响应格式的一致性。

#### Scenario: 成功的研究编排响应
- **WHEN** 研究编排请求成功完成
- **THEN** 系统返回 `BaseResponse[ResearchOrchestrationResponse]`，其中：
  - `success: true`
  - `message: "研究编排成功完成"`
  - `code: "RESEARCH_ORCHESTRATION_SUCCESS"`
  - `data: ResearchOrchestrationResponse` 包含研究结果的详细信息

#### Scenario: 研究编排失败响应
- **WHEN** 研究编排过程中发生错误
- **THEN** 系统返回 `ErrorResponse`，包含：
  - `success: false`
  - `message: str` 具体的错误描述
  - `code: str` 对应的错误代码（如 "EXPERTS_ALL_FAILED"、"SESSION_NOT_FOUND" 等）

#### Scenario: 研究重试响应格式
- **WHEN** 研究重试请求完成
- **THEN** 系统返回 `BaseResponse[ResearchOrchestrationResponse]`，格式与正常编排响应保持一致
