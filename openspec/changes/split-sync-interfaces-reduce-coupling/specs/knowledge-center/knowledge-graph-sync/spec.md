## MODIFIED Requirements

### Requirement: 同步通过 REST API 触发

系统 SHALL 提供 REST 端点触发图谱同步，包括原有接口（标记为 deprecated）和新增的专用端点。

**原有接口（deprecated）**：
```
POST /api/v1/knowledge-graph/sync
Body: { "mode": "full" | "incremental", "third_codes": ["..."], "target": "stock" | "concept" | "all" }
```

**新增专用端点**：
```
POST /api/v1/knowledge-graph/sync/stocks/full        # 股票全量同步
POST /api/v1/knowledge-graph/sync/stocks/incremental # 股票增量同步
POST /api/v1/knowledge-graph/sync/concepts            # 概念同步
POST /api/v1/knowledge-graph/sync/all                 # 全部同步
```

原有接口 SHALL 继续支持，用于向后兼容，但 SHOULD 在 OpenAPI 文档中标记为 deprecated。新客户端 SHOULD 使用专用端点。

#### Scenario: 通过 API 触发全量同步（默认行为不变）
- **WHEN** 发送 `POST /api/v1/knowledge-graph/sync` 且 body 为 `{"mode": "full"}`
- **THEN** 系统执行全量股票元数据同步并返回 200 及同步结果摘要（行为与变更前一致）

#### Scenario: 通过 API 触发概念同步
- **WHEN** 发送 `POST /api/v1/knowledge-graph/sync` 且 body 为 `{"mode": "full", "target": "concept"}`
- **THEN** 系统执行概念全量同步并返回 200 及概念同步结果摘要

#### Scenario: 通过 API 触发增量同步
- **WHEN** 发送 `POST /api/v1/knowledge-graph/sync` 且 body 为 `{"mode": "incremental", "third_codes": ["000001.SZ"]}`
- **THEN** 系统仅同步指定股票并返回 200 及同步结果摘要

#### Scenario: 通过 API 触发全部同步
- **WHEN** 发送 `POST /api/v1/knowledge-graph/sync` 且 body 为 `{"mode": "full", "target": "all"}`
- **THEN** 系统依次执行股票全量同步和概念全量同步，返回 200 及合并的同步结果摘要

## ADDED Requirements

### Requirement: 原有同步接口标记为 deprecated
系统 SHALL 在 OpenAPI 文档中将 `POST /api/v1/knowledge-graph/sync` 标记为 deprecated，并在描述中建议使用新的专用端点。

#### Scenario: OpenAPI 文档显示 deprecated 标记
- **WHEN** 查看 OpenAPI 文档
- **THEN** `POST /api/v1/knowledge-graph/sync` 端点显示 deprecated 标记
- **THEN** 端点描述中包含建议使用新专用端点的说明
