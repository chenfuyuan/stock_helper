# Purpose

提供专用的股票增量同步接口，简化参数结构，提升 API 易用性。

## Requirements

### Requirement: 股票增量同步专用端点

系统 SHALL 提供专用的 REST 端点用于股票增量同步：

```
POST /api/v1/knowledge-graph/sync/stocks/incremental
```

请求体 MUST 包含以下参数：
- `third_codes`（可选）：股票代码列表；为空时按时间窗口自动确定
- `include_finance`（可选）：是否包含财务快照数据，默认 false
- `batch_size`（可选）：批量大小，默认 500
- `window_days`（可选）：自动模式下时间窗口天数，默认 3
- `limit`（可选）：自动模式下扫描上限，默认 10000

响应体 MUST 返回同步结果摘要，与现有同步响应格式一致。

#### Scenario: 按指定股票代码增量同步
- **WHEN** 发送 `POST /api/v1/knowledge-graph/sync/stocks/incremental` 且 body 为 `{"third_codes": ["000001.SZ", "601398.SH"]}`
- **THEN** 系统仅同步指定的两支股票并返回 200 及同步结果摘要

#### Scenario: 按时间窗口自动增量同步
- **WHEN** 发送 `POST /api/v1/knowledge-graph/sync/stocks/incremental` 且 body 为 `{"window_days": 7, "limit": 1000}`
- **THEN** 系统同步最近 7 天内有变更的股票，最多 1000 支

#### Scenario: 带财务数据的增量同步
- **WHEN** 发送 `POST /api/v1/knowledge-graph/sync/stocks/incremental` 且 body 为 `{"third_codes": ["000001.SZ"], "include_finance": true}`
- **THEN** 系统同步指定股票及其财务快照数据
