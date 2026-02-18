# Purpose

提供专用的概念同步接口，简化参数结构，提升 API 易用性。

## Requirements

### Requirement: 概念同步专用端点

系统 SHALL 提供专用的 REST 端点用于概念同步：

```
POST /api/v1/knowledge-graph/sync/concepts
```

请求体 MUST 包含以下参数：
- `batch_size`（可选）：批量大小，默认 500

概念同步仅支持全量模式，不支持增量。

响应体 MUST 返回同步结果摘要，与现有同步响应格式一致。

#### Scenario: 正常概念同步
- **WHEN** 发送 `POST /api/v1/knowledge-graph/sync/concepts`
- **THEN** 系统执行概念全量同步（先删除旧关系，再重建）并返回 200 及同步结果摘要

#### Scenario: 带批量大小的概念同步
- **WHEN** 发送 `POST /api/v1/knowledge-graph/sync/concepts` 且 body 为 `{"batch_size": 1000}`
- **THEN** 系统使用指定的批量大小执行概念同步

#### Scenario: 概念数据为空时返回空结果
- **WHEN** PostgreSQL 中无概念数据，触发概念同步
- **THEN** 系统记录 WARNING 日志并返回空结果（概念总数 = 0），不抛出异常
