## MODIFIED Requirements

### Requirement: 辩论响应格式
辩论模块的所有接口 SHALL 返回统一的 `BaseResponse[T]` 格式，确保与其他 API 接口响应格式的一致性。

#### Scenario: 多头辩论响应
- **WHEN** 多头辩论请求成功完成
- **THEN** 系统返回 `BaseResponse[BullAdvocateResult]`，其中：
  - `success: true`
  - `message: "多头辩论成功完成"`
  - `code: "BULL_ADVOCATE_SUCCESS"`
  - `data: BullAdvocateResult` 包含多头观点分析结果

#### Scenario: 空头辩论响应
- **WHEN** 空头辩论请求成功完成
- **THEN** 系统返回 `BaseResponse[BearAdvocateResult]`，其中：
  - `success: true`
  - `message: "空头辩论成功完成"`
  - `code: "BEAR_ADVOCATE_SUCCESS"`
  - `data: BearAdvocateResult` 包含空头观点分析结果

#### Scenario: 辩论裁决响应
- **WHEN** 辩论裁决请求成功完成
- **THEN** 系统返回 `BaseResponse[DebateResolutionResult]`，其中：
  - `success: true`
  - `message: "辩论裁决成功完成"`
  - `code: "DEBATE_RESOLUTION_SUCCESS"`
  - `data: DebateResolutionResult` 包含辩论裁决结果

#### Scenario: 辩论失败响应
- **WHEN** 辩论过程中发生错误
- **THEN** 系统返回 `ErrorResponse`，包含：
  - `success: false`
  - `message: str` 辩论失败的具体描述
  - `code: str` 对应的错误代码（如 "DEBATE_TIMEOUT"、"ARGUMENT_GENERATION_FAILED" 等）
