## MODIFIED Requirements

### Requirement: 研究分析响应格式
研究分析模块的所有接口 SHALL 返回统一的 `BaseResponse[T]` 格式，确保与其他 API 接口响应格式的一致性。

#### Scenario: 技术分析响应
- **WHEN** 技术分析请求成功完成
- **THEN** 系统返回 `BaseResponse[TechnicalAnalysisResult]`，其中：
  - `success: true`
  - `message: "技术分析成功完成"`
  - `code: "TECHNICAL_ANALYSIS_SUCCESS"`
  - `data: TechnicalAnalysisResult` 包含技术分析结果

#### Scenario: 估值建模响应
- **WHEN** 估值建模请求成功完成
- **THEN** 系统返回 `BaseResponse[ValuationModelResult]`，其中：
  - `success: true`
  - `message: "估值建模成功完成"`
  - `code: "VALUATION_MODEL_SUCCESS"`
  - `data: ValuationModelResult` 包含估值结果

#### Scenario: 财务审计响应
- **WHEN** 财务审计请求成功完成
- **THEN** 系统返回 `BaseResponse[FinancialAuditResult]`，其中：
  - `success: true`
  - `message: "财务审计成功完成"`
  - `code: "FINANCIAL_AUDIT_SUCCESS"`
  - `data: FinancialAuditResult` 包含审计结果

#### Scenario: 催化剂侦探响应
- **WHEN** 催化剂侦探请求成功完成
- **THEN** 系统返回 `BaseResponse[CatalystDetectiveResult]`，其中：
  - `success: true`
  - `message: "催化剂侦探成功完成"`
  - `code: "CATALYST_DETECTIVE_SUCCESS"`
  - `data: CatalystDetectiveResult` 包含催化剂分析结果

#### Scenario: 宏观情报响应
- **WHEN** 宏观情报请求成功完成
- **THEN** 系统返回 `BaseResponse[MacroIntelligenceResult]`，其中：
  - `success: true`
  - `message: "宏观情报成功完成"`
  - `code: "MACRO_INTELLIGENCE_SUCCESS"`
  - `data: MacroIntelligenceResult` 包含宏观分析结果

#### Scenario: 研究分析失败响应
- **WHEN** 研究分析过程中发生错误
- **THEN** 系统返回 `ErrorResponse`，包含：
  - `success: false`
  - `message: str` 研究分析失败的具体描述
  - `code: str` 对应的错误代码（如 "DATA_NOT_AVAILABLE"、"MODEL_ERROR" 等）
