## Why

当前知识图谱同步接口 `/knowledge-graph/sync` 存在参数耦合度高的问题：一个请求体包含多种模式的混合参数，参数有效条件复杂，容易误用。例如 `target="concept"` 时会忽略 `mode`、`third_codes` 等参数，导致 API 不够直观和易用。

## What Changes

- **新增** 4 个专用的同步端点，替代原来的单一接口
- **保留** 原 `/knowledge-graph/sync` 接口（标记为 deprecated），实现向后兼容
- **新增** 清晰的请求/响应 DTO，每个端点有专用的数据结构
- **更新** 路由层逻辑，分发请求到新的专用端点处理逻辑

**BREAKING**: 虽然原接口会保留并标记为 deprecated，但建议客户端尽快迁移到新接口。

## Capabilities

### New Capabilities
- `knowledge-graph-sync-stocks-full`: 股票全量同步专用接口
- `knowledge-graph-sync-stocks-incremental`: 股票增量同步专用接口
- `knowledge-graph-sync-concepts`: 概念同步专用接口
- `knowledge-graph-sync-all`: 全部同步专用接口

### Modified Capabilities
- `knowledge-center/knowledge-graph-sync`: 更新同步接口设计规范，描述新的专用端点

## Impact

- **受影响代码**: `src/modules/knowledge_center/presentation/rest/graph_router.py`
- **受影响 API**: `POST /knowledge-graph/sync`（保留但 deprecated）
- **新增 API**: 4 个新的同步端点
- **受影响 DTO**: `src/modules/knowledge_center/application/dtos/graph_api_dtos.py`（需新增专用 DTO）
