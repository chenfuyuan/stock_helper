## MODIFIED Requirements

### Requirement: 市场洞察响应格式
市场洞察模块的所有接口 SHALL 返回统一的 `BaseResponse[T]` 格式，确保与其他 API 接口响应格式的一致性。

#### Scenario: 市场趋势分析响应
- **WHEN** 市场趋势分析请求成功完成
- **THEN** 系统返回 `BaseResponse[MarketTrendResult]`，其中：
  - `success: true`
  - `message: "市场趋势分析成功完成"`
  - `code: "MARKET_TREND_SUCCESS"`
  - `data: MarketTrendResult` 包含市场趋势分析结果

#### Scenario: 板块轮动分析响应
- **WHEN** 板块轮动分析请求成功完成
- **THEN** 系统返回 `BaseResponse[SectorRotationResult]`，其中：
  - `success: true`
  - `message: "板块轮动分析成功完成"`
  - `code: "SECTOR_ROTATION_SUCCESS"`
  - `data: SectorRotationResult` 包含板块轮动分析结果

#### Scenario: 市场情绪分析响应
- **WHEN** 市场情绪分析请求成功完成
- **THEN** 系统返回 `BaseResponse[MarketSentimentResult]`，其中：
  - `success: true`
  - `message: "市场情绪分析成功完成"`
  - `code: "MARKET_SENTIMENT_SUCCESS"`
  - `data: MarketSentimentResult` 包含市场情绪分析结果

#### Scenario: 市场洞察失败响应
- **WHEN** 市场洞察分析过程中发生错误
- **THEN** 系统返回 `ErrorResponse`，包含：
  - `success: false`
  - `message: str` 市场洞察分析失败的具体描述
  - `code: str` 对应的错误代码（如 "MARKET_DATA_UNAVAILABLE"、"ANALYSIS_ERROR" 等）
