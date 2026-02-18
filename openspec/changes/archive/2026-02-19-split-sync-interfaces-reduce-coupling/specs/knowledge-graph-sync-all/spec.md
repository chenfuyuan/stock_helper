# Purpose

提供专用的全部同步接口，简化参数结构，提升 API 易用性。

## Requirements

### Requirement: 全部同步专用端点

系统 SHALL 提供专用的 REST 端点用于全部同步（股票 + 概念）：

```
POST /api/v1/knowledge-graph/sync/all
```

请求体 MUST 包含以下参数：
- `mode`（必填）：股票同步模式，`full`（全量）或 `incremental`（增量）
- `include_finance`（可选）：是否包含财务快照数据，默认 false
- `batch_size`（可选）：批量大小，默认 500
- `third_codes`（可选，仅 mode=incremental 时有效）：股票代码列表
- `window_days`（可选，仅 mode=incremental 时有效）：自动模式下时间窗口天数，默认 3
- `skip`（可选，仅 mode=full 时有效）：跳过前 N 条记录，默认 0
- `limit`（可选）：扫描/查询数量上限，默认 10000

全部同步 SHALL 依次执行：
1. 股票同步（根据 mode 参数）
2. 概念全量同步

响应体 MUST 返回合并后的同步结果摘要。

#### Scenario: 全部全量同步
- **WHEN** 发送 `POST /api/v1/knowledge-graph/sync/all` 且 body 为 `{"mode": "full", "include_finance": true}`
- **THEN** 系统依次执行股票全量同步和概念全量同步，返回 200 及合并的同步结果摘要

#### Scenario: 全部增量同步
- **WHEN** 发送 `POST /api/v1/knowledge-graph/sync/all` 且 body 为 `{"mode": "incremental", "third_codes": ["000001.SZ"]}`
- **THEN** 系统依次执行指定股票的增量同步和概念全量同步

#### Scenario: 部分失败的全部同步
- **WHEN** 全部同步中股票同步成功但概念同步失败
- **THEN** 返回合并结果，包含各自的成功/失败统计和错误详情
