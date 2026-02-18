## MODIFIED Requirements

### Requirement: 裁决响应格式
裁决模块的所有接口 SHALL 返回统一的 `BaseResponse[T]` 格式，确保与其他 API 接口响应格式的一致性。

#### Scenario: 投资裁决响应
- **WHEN** 投资裁决请求成功完成
- **THEN** 系统返回 `BaseResponse[InvestmentVerdictResult]`，其中：
  - `success: true`
  - `message: "投资裁决成功完成"`
  - `code: "INVESTMENT_VERDICT_SUCCESS"`
  - `data: InvestmentVerdictResult` 包含投资裁决结果

#### Scenario: 风险评估响应
- **WHEN** 风险评估请求成功完成
- **THEN** 系统返回 `BaseResponse[RiskAssessmentResult]`，其中：
  - `success: true`
  - `message: "风险评估成功完成"`
  - `code: "RISK_ASSESSMENT_SUCCESS"`
  - `data: RiskAssessmentResult` 包含风险评估结果

#### Scenario: 裁决失败响应
- **WHEN** 裁决过程中发生错误
- **THEN** 系统返回 `ErrorResponse`，包含：
  - `success: false`
  - `message: str` 裁决失败的具体描述
  - `code: str` 对应的错误代码（如 "VERDICT_GENERATION_FAILED"、"INSUFFICIENT_DATA" 等）
