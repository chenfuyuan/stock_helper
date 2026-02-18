# Purpose

提供专用的股票全量同步接口，简化参数结构，提升 API 易用性。

## Requirements

### Requirement: 股票全量同步专用端点

系统 SHALL 提供专用的 REST 端点用于股票全量同步：

```
POST /api/v1/knowledge-graph/sync/stocks/full
```

请求体 MUST 包含以下参数：
- `include_finance`（可选）：是否包含财务快照数据，默认 false
- `batch_size`（可选）：批量大小，默认 500
- `skip`（可选）：跳过前 N 条记录，默认 0
- `limit`（可选）：查询数量上限，默认 10000

响应体 MUST 返回同步结果摘要，与现有同步响应格式一致。

#### Scenario: 正常全量同步
- **WHEN** 发送 `POST /api/v1/knowledge-graph/sync/stocks/full` 且 body 为 `{"include_finance": true}`
- **THEN** 系统执行股票全量同步并返回 200 及同步结果摘要

#### Scenario: 带分页参数的全量同步
- **WHEN** 发送 `POST /api/v1/knowledge-graph/sync/stocks/full` 且 body 为 `{"skip": 1000, "limit": 500}`
- **THEN** 系统从第 1001 条记录开始同步，最多同步 500 条

#### Scenario: 同步失败返回错误
- **WHEN** 同步过程中发生 Neo4j 连接错误
- **THEN** 返回 HTTP 500 及错误信息
