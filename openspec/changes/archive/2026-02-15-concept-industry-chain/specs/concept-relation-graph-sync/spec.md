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

### Requirement: IGraphRepository 扩展概念关系同步方法

`IGraphRepository` 接口 MUST 新增以下方法：

- `merge_concept_relations(relations: list[ConceptRelationSyncDTO]) -> SyncResult`：批量写入/更新 Concept 间关系
- `delete_all_concept_inter_relationships() -> int`：删除所有 Concept 间关系（不影响 Stock-Concept 关系）

#### Scenario: merge_concept_relations 写入关系

- **WHEN** 调用 `merge_concept_relations()` 传入 3 条关系数据
- **THEN** Neo4j 中 MUST 存在对应的 3 条 Concept 间关系
- **THEN** 每条关系的类型 MUST 与 `relation_type` 对应（如 `IS_UPSTREAM_OF`）

#### Scenario: merge_concept_relations 更新已有关系

- **WHEN** 对同一对概念的同类型关系再次调用 `merge_concept_relations()`
- **THEN** 关系属性（confidence、source_type）MUST 更新为新值
- **THEN** 不创建重复关系

#### Scenario: delete_all_concept_inter_relationships 仅删 Concept 间关系

- **WHEN** 调用 `delete_all_concept_inter_relationships()`
- **THEN** Neo4j 中所有 `(Concept)-[*]->(Concept)` 的关系 MUST 被删除
- **THEN** `(Stock)-[:BELONGS_TO_CONCEPT]->(Concept)` 关系 MUST 保留不变
- **THEN** Concept 节点本身 MUST 保留

### Requirement: ConceptRelationSyncDTO 定义

系统 MUST 在 `knowledge_center/domain/dtos/concept_relation_sync_dtos.py` 中定义 `ConceptRelationSyncDTO`（Pydantic BaseModel）。

字段 MUST 包含：

- `pg_id`（int）：PostgreSQL 中的主键 ID
- `source_concept_code`（str）
- `target_concept_code`（str）
- `relation_type`（ConceptRelationType）
- `source_type`（RelationSourceType）
- `confidence`（float）

#### Scenario: DTO 字段完整

- **WHEN** 从 PostgreSQL 查询已确认关系并转换为 `ConceptRelationSyncDTO`
- **THEN** 每条 DTO MUST 包含 `pg_id`、`source_concept_code`、`target_concept_code`、`relation_type`、`source_type`、`confidence`

### Requirement: Neo4j 批量写入策略

概念关系同步 MUST 使用批量写入策略，避免逐条事务提交。

- MUST 使用 Cypher `UNWIND + MATCH + MERGE` 模式：MATCH 两端 Concept 节点，MERGE 关系
- 批量大小 SHALL 可配置，默认值为 200
- 仅当两端 Concept 节点均存在时才创建关系

#### Scenario: 批量写入概念关系

- **WHEN** 同步 100 条概念关系
- **THEN** 系统 MUST 使用批量操作写入，不 SHALL 逐条提交

#### Scenario: Concept 节点不存在时跳过

- **WHEN** 某条关系的 `source_concept_code` 或 `target_concept_code` 在 Neo4j 中无对应 Concept 节点
- **THEN** 该条关系 MUST 被跳过
- **THEN** 跳过情况 MUST 被记录到日志（WARNING 级别）

### Requirement: REST API — 同步概念关系到 Neo4j

系统 SHALL 提供 REST 端点：

```
POST /api/v1/knowledge-graph/concept-relations/sync
```

请求体 MUST 包含：

- `mode`（str, 必填）：同步模式，枚举 `rebuild` / `incremental`
- `relation_ids`（list[int], 可选）：仅 `mode = incremental` 时有效，指定要同步的关系 ID

#### Scenario: 触发全量重建同步

- **WHEN** 发送 `POST /api/v1/knowledge-graph/concept-relations/sync` 且 body 为 `{"mode": "rebuild"}`
- **THEN** 返回 HTTP 200 及同步结果摘要

#### Scenario: 触发增量同步

- **WHEN** 发送 `POST /api/v1/knowledge-graph/concept-relations/sync` 且 body 为 `{"mode": "incremental", "relation_ids": [1, 2, 3]}`
- **THEN** 返回 HTTP 200 及同步结果摘要

#### Scenario: 无效同步模式返回 422

- **WHEN** 发送 `{"mode": "invalid"}`
- **THEN** 返回 HTTP 422
