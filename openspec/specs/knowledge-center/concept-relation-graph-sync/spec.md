# Purpose

将 PostgreSQL 中已确认的概念关系同步到 Neo4j 图谱，构建 Concept 间的关系网络。Neo4j 为派生查询视图，支持从 PostgreSQL 全量重建。

## ADDED Requirements

### Requirement: SyncConceptRelationsCmd 同步命令

系统 MUST 在 `knowledge_center/application/commands/sync_concept_relations_command.py` 中实现 `SyncConceptRelationsCmd`。

该命令 MUST 支持两种同步模式：

1. **全量重建（rebuild）**：
   - 删除 Neo4j 中所有 Concept 间关系（`IS_UPSTREAM_OF`、`IS_DOWNSTREAM_OF`、`COMPETES_WITH`、`IS_PART_OF`、`ENABLER_FOR`）
   - 从 PostgreSQL 读取所有 `status = CONFIRMED` 的 `concept_relation` 记录
   - 批量写入 Neo4j

2. **增量追加（incremental）**：
   - 从 PostgreSQL 读取指定 ID 列表或自上次同步后新增/变更的已确认关系
   - 逐条 MERGE 到 Neo4j（已存在则更新属性）

#### Scenario: 全量重建同步

- **WHEN** 触发全量重建同步且 PostgreSQL 中有 50 条 CONFIRMED 关系
- **THEN** Neo4j 中旧的 Concept 间关系 MUST 先被全部删除
- **THEN** Neo4j 中 MUST 创建 50 条对应的 Concept 间关系
- **THEN** 每条关系 MUST 携带 `source_type`、`confidence`、`pg_id` 属性

#### Scenario: 全量重建可从零恢复 Neo4j

- **WHEN** Neo4j 图谱中 Concept 间关系为空（如 Neo4j 被重建）
- **THEN** 全量重建 MUST 从 PostgreSQL 完整恢复所有已确认的 Concept 间关系
- **THEN** 恢复后的关系数量 MUST 等于 PostgreSQL 中 `status = CONFIRMED` 的记录数

#### Scenario: 增量同步指定 ID

- **WHEN** 触发增量同步，指定 `relation_ids = [1, 2, 3]`
- **THEN** 仅查询这 3 条记录中 `status = CONFIRMED` 的记录
- **THEN** 将其 MERGE 到 Neo4j（已存在则更新，不存在则创建）

#### Scenario: PENDING 和 REJECTED 的关系不同步

- **WHEN** PostgreSQL 中有 `status = PENDING` 或 `status = REJECTED` 的关系
- **THEN** 这些关系 MUST NOT 被同步到 Neo4j

#### Scenario: 同步完成后报告结果

- **WHEN** 同步命令执行完毕
- **THEN** MUST 返回同步结果摘要：同步模式、写入数量、删除数量（仅全量重建）、总耗时

### Requirement: Neo4j GraphRepository 扩展

系统 MUST 在 `knowledge_center/infrastructure/persistence/neo4j_graph_repository.py` 中扩展 `Neo4jGraphRepository`，支持概念关系操作。

新增方法 MUST 包含：

- `delete_all_concept_inter_relationships()`：删除所有 Concept 间关系
- `merge_concept_relations(relations: list[ConceptRelationSyncDTO], batch_size: int)`：批量 MERGE 概念关系
- `get_concept_relations(concept_code: str, direction: str, relation_types: list[str] | None)`：查询概念关系
- `find_concept_chain(concept_code: str, direction: str, max_depth: int)`：查询概念产业链路径

`ConceptRelationSyncDTO` MUST 包含：

- `pg_id`（int）：PostgreSQL 记录 ID
- `source_concept_code`（str）
- `target_concept_code`（str）
- `relation_type`（str）
- `source_type`（str）
- `confidence`（float）

#### Scenario: 批量 MERGE 性能优化

- **WHEN** 批量 MERGE 1000 条概念关系，batch_size=100
- **THEN** MUST 分 10 个批次执行，每批次 100 条
- **THEN** 每批次使用单个事务提交
- **THEN** 返回的 SyncResult MUST 包含成功数量和失败数量

#### Scenario: 关系类型过滤查询

- **WHEN** 调用 `get_concept_relations(concept_code="BK0001", direction="outgoing", relation_types=["IS_UPSTREAM_OF"])`
- **THEN** 返回 BK0001 的所有上游关系
- **THEN** 不返回其他类型的关系

#### Scenario: 产业链路径查询

- **WHEN** 调用 `find_concept_chain(concept_code="BK0001", direction="outgoing", max_depth=3)`
- **THEN** 返回从 BK0001 出发，深度不超过 3 的所有可达概念
- **THEN** 结果 MUST 包含路径深度和每一步的关系类型

### Requirement: REST API — 同步概念关系

系统 SHALL 提供 REST 端点：

```
POST /api/v1/knowledge-graph/concept-relations/sync
```

请求体 MUST 包含：

- `mode`（str，必填）：`"rebuild"` 或 `"incremental"`
- `batch_size`（int，可选，默认 500）：批量处理大小

#### Scenario: 全量重建同步

- **WHEN** 发送 `{"mode": "rebuild", "batch_size": 100}`
- **THEN** 返回 HTTP 200 及同步结果
- **THEN** Neo4j 中所有旧的 Concept 间关系 MUST 被删除
- **THEN** PostgreSQL 中所有 CONFIRMED 关系 MUST 被同步到 Neo4j

#### Scenario: 增量同步

- **WHEN** 发送 `{"mode": "incremental", "batch_size": 200}`
- **THEN** 返回 HTTP 200 及同步结果
- **THEN** 仅同步新增或变更的 CONFIRMED 关系
- **THEN** 保留 Neo4j 中现有的关系

#### Scenario: 同步结果统计

- **WHEN** 同步完成
- **THEN** 返回结果 MUST 包含：
  - `mode`：同步模式
  - `total_relations`：从 PostgreSQL 读取的关系数
  - `sync_success`：成功写入 Neo4j 的数量
  - `sync_failed`：写入失败的数量
  - `duration_ms`：总耗时（毫秒）

### Requirement: REST API — 查询概念关系网络

系统 SHALL 提供 REST 端点：

```
GET /api/v1/knowledge-graph/concepts/{concept_code}/relations
```

查询参数：

- `direction`（可选，默认 `"outgoing"`）：`"outgoing"` 或 `"incoming"`
- `relation_types`（可选）：关系类型列表，逗号分隔

#### Scenario: 查询概念的所有出向关系

- **WHEN** 发送 `GET /api/v1/knowledge-graph/concepts/BK0001/relations`
- **THEN** 返回 BK0001 的所有出向关系
- **THEN** 每条关系包含目标概念、关系类型、置信度等信息

#### Scenario: 查询概念的入向关系

- **WHEN** 发送 `GET /api/v1/knowledge-graph/concepts/BK0001/relations?direction=incoming`
- **THEN** 返回 BK0001 的所有入向关系
- **THEN** 每条关系包含源概念、关系类型、置信度等信息

### Requirement: REST API — 查询概念产业链路径

系统 SHALL 提供 REST 端点：

```
GET /api/v1/knowledge-graph/concepts/{concept_code}/chain
```

查询参数：

- `direction`（可选，默认 `"outgoing"`）：`"outgoing"` 或 `"incoming"`
- `max_depth`（可选，默认 3）：最大路径深度

#### Scenario: 查询上游产业链

- **WHEN** 发送 `GET /api/v1/knowledge-graph/concepts/BK0003/chain?direction=incoming&max_depth=2`
- **THEN** 返回 BK0003 的上游产业链路径，深度不超过 2
- **THEN** 结果 MUST 按深度排序，包含每步的关系类型

#### Scenario: 查询下游产业链

- **WHEN** 发送 `GET /api/v1/knowledge-graph/concepts/BK0001/chain?direction=outgoing&max_depth=3`
- **THEN** 返回 BK0001 的下游产业链路径，深度不超过 3
- **THEN** 结果 MUST 包含所有可达概念及其路径信息

### Requirement: DI Container 注册

`KnowledgeCenterContainer` MUST 注册以下新增组件：

- `SyncConceptRelationsCmd` 应用命令

#### Scenario: 命令可注入

- **WHEN** 通过 DI 容器请求 `SyncConceptRelationsCmd` 实例
- **THEN** MUST 返回已注入所有依赖的命令实例
