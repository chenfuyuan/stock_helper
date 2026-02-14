# Purpose

扩展知识图谱同步管道，新增概念题材数据同步能力。

## ADDED Requirements

### Requirement: 概念数据全量同步命令

系统 SHALL 提供概念图谱全量同步命令（`SyncConceptGraphCmd`），从 `data_engineering` 的 PostgreSQL（通过适配器）读取概念板块数据并写入 Neo4j 图谱。

前置条件：概念数据已通过 DE 模块的 `SyncConceptDataCmd` 同步到 PostgreSQL。

同步 MUST 包含以下步骤：

1. 通过 KC 适配器调用 DE 的 `IConceptRepository.get_all_concepts_with_stocks()` 获取所有概念及成份股
2. 删除 Neo4j 中所有现有的 `BELONGS_TO_CONCEPT` 关系（先清策略）
3. 批量 MERGE Concept 节点（by code）
4. 批量创建 `(Stock)-[:BELONGS_TO_CONCEPT]->(Concept)` 关系（仅当 Stock 节点已存在时）

#### Scenario: 首次概念图谱同步

- **WHEN** 用户触发概念图谱同步且 Neo4j 中无 Concept 节点
- **THEN** 系统从 DE 的 PostgreSQL 读取所有概念板块及成份股
- **THEN** Neo4j 中 MUST 创建对应的 Concept 节点和 BELONGS_TO_CONCEPT 关系

#### Scenario: 重复概念同步保持一致

- **WHEN** 对已存在概念数据的图谱再次执行全量同步
- **THEN** 旧的 BELONGS_TO_CONCEPT 关系 MUST 先被全部删除
- **THEN** 基于 PostgreSQL 中的最新数据重建所有 Concept 节点（MERGE）和关系
- **THEN** 若某股票已从某概念中移除，新图谱中 MUST NOT 存在该陈旧关系

#### Scenario: PostgreSQL 无概念数据时

- **WHEN** 触发概念图谱同步但 DE 的 PostgreSQL 中无概念数据
- **THEN** 同步命令 MUST 记录 WARNING 日志并返回空结果（概念总数 = 0），不抛出异常

#### Scenario: 同步完成后报告结果

- **WHEN** 概念同步命令执行完毕
- **THEN** MUST 返回同步结果摘要，包含：概念总数、Concept 节点数、创建的关系总数、总耗时

### Requirement: 概念同步的批量写入

概念同步管道 MUST 使用批量写入策略，避免逐条事务提交。

- Concept 节点 MUST 使用 Cypher `UNWIND + MERGE` 批量写入
- BELONGS_TO_CONCEPT 关系 MUST 使用 Cypher `UNWIND + MATCH + MERGE` 批量写入（MATCH Stock 节点，仅当存在时创建关系）

#### Scenario: 批量写入概念节点

- **WHEN** 同步 300 个概念板块
- **THEN** 系统 MUST 使用批量操作写入，不 SHALL 逐条提交

#### Scenario: 批量写入概念关系

- **WHEN** 某概念有 50 个成份股
- **THEN** 系统 MUST 通过 UNWIND 一次性写入该概念的所有 Stock-Concept 关系

### Requirement: 跨模块概念数据读取通过 Adapter

`knowledge_center` 从 `data_engineering` 获取概念数据 MUST 通过 `knowledge_center/infrastructure/adapters/` 下的适配器完成。

适配器 MUST 注入 DE 的 `IConceptRepository`（或 DE 暴露的应用服务），调用 `get_all_concepts_with_stocks()` 查询 PostgreSQL 中的概念数据。

适配器 MUST 将 `data_engineering` 的 DTO（`ConceptWithStocksDTO`）转换为 `knowledge_center` 的 `domain/dtos/` 中定义的同步 DTO（`ConceptGraphSyncDTO`）。`knowledge_center` 的 Domain 层 MUST NOT import `data_engineering` 的任何类型。

#### Scenario: Adapter 从 PostgreSQL 读取数据

- **WHEN** Adapter 被调用获取概念数据
- **THEN** 实际数据来源 MUST 为 DE 模块的 PostgreSQL（`concept` + `concept_stock` 表）
- **THEN** 返回的 DTO 类型 MUST 属于 `knowledge_center.domain.dtos` 包

#### Scenario: Domain 层无跨模块依赖

- **WHEN** 检查 `knowledge_center` 的 Domain 层代码
- **THEN** MUST NOT 存在对 `data_engineering` 模块类型的 import

### Requirement: IGraphRepository 扩展概念同步方法

`IGraphRepository` 接口 MUST 新增以下方法：

- `merge_concepts(concepts: list[ConceptGraphSyncDTO]) -> SyncResult`：批量写入/更新 Concept 节点及其与 Stock 的关系
- `delete_all_concept_relationships() -> int`：删除所有 BELONGS_TO_CONCEPT 关系，返回删除数量

#### Scenario: merge_concepts 写入概念数据

- **WHEN** 调用 `merge_concepts()` 传入概念数据列表
- **THEN** Neo4j 中 MUST 存在对应的 Concept 节点和 BELONGS_TO_CONCEPT 关系

#### Scenario: delete_all_concept_relationships 清理关系

- **WHEN** 调用 `delete_all_concept_relationships()`
- **THEN** Neo4j 中所有 `BELONGS_TO_CONCEPT` 关系 MUST 被删除
- **THEN** Concept 节点本身 MUST 保留（仅删关系）
- **THEN** 返回值为被删除的关系数量

## MODIFIED Requirements

### Requirement: 同步通过 REST API 触发

系统 SHALL 提供 REST 端点触发图谱同步：

```
POST /api/v1/knowledge-graph/sync
Body: { "mode": "full" | "incremental", "third_codes": ["..."], "target": "stock" | "concept" | "all" }
```

`third_codes` 仅在 `mode = "incremental"` 且 `target = "stock"` 时有效，为空时根据时间窗口自动确定范围。

`target` 为可选参数，默认值为 `"stock"`：

- `"stock"`：执行现有的股票元数据同步（行为不变）
- `"concept"`：执行概念数据全量同步（忽略 `mode` 和 `third_codes`，概念同步仅支持全量模式）
- `"all"`：依次执行股票同步和概念同步

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
