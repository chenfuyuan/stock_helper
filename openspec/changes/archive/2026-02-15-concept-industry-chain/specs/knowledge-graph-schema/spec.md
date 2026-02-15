# Purpose

扩展知识图谱 Schema，新增 Concept 节点间的关系类型定义。

## ADDED Requirements

### Requirement: Concept 间关系类型定义

系统 SHALL 在 Neo4j 中支持 Concept 节点之间的以下关系类型：

- `IS_UPSTREAM_OF`：上游关系。方向为 `(Concept)-[:IS_UPSTREAM_OF]->(Concept)`，表示源概念是目标概念的上游。
- `IS_DOWNSTREAM_OF`：下游关系。方向为 `(Concept)-[:IS_DOWNSTREAM_OF]->(Concept)`，表示源概念是目标概念的下游。
- `COMPETES_WITH`：竞争关系。方向为 `(Concept)-[:COMPETES_WITH]->(Concept)`。
- `IS_PART_OF`：组成部分关系。方向为 `(Concept)-[:IS_PART_OF]->(Concept)`，表示源概念是目标概念的组成部分。
- `ENABLER_FOR`：技术驱动关系。方向为 `(Concept)-[:ENABLER_FOR]->(Concept)`，表示源概念为目标概念提供技术支撑。

#### Scenario: 创建上游关系

- **WHEN** 同步管道写入"锂电池"(BK0001) IS_UPSTREAM_OF "新能源车"(BK0002)
- **THEN** Neo4j 中 MUST 存在 `(:Concept {code: "BK0001"})-[:IS_UPSTREAM_OF]->(:Concept {code: "BK0002"})` 关系

#### Scenario: 创建竞争关系

- **WHEN** 同步管道写入"磷酸铁锂"(BK0003) COMPETES_WITH "三元锂电"(BK0004)
- **THEN** Neo4j 中 MUST 存在 `(:Concept {code: "BK0003"})-[:COMPETES_WITH]->(:Concept {code: "BK0004"})` 关系

#### Scenario: 创建技术驱动关系

- **WHEN** 同步管道写入"半导体"(BK0005) ENABLER_FOR "人工智能"(BK0006)
- **THEN** Neo4j 中 MUST 存在 `(:Concept {code: "BK0005"})-[:ENABLER_FOR]->(:Concept {code: "BK0006"})` 关系

### Requirement: Concept 间关系属性定义

所有 Concept 间关系 MUST 携带以下属性：

- `source_type`（String）：来源类型（`MANUAL` / `LLM`）
- `confidence`（Float）：置信度（0.0~1.0）
- `pg_id`（Integer）：对应 PostgreSQL `concept_relation` 表的主键 ID，用于反向追溯

#### Scenario: 关系携带属性

- **WHEN** 同步一条来源为 LLM、置信度为 0.85 的关系，PostgreSQL 主键为 42
- **THEN** Neo4j 关系 MUST 包含属性 `{source_type: "LLM", confidence: 0.85, pg_id: 42}`

#### Scenario: 通过 pg_id 反向追溯

- **WHEN** 在 Neo4j 中查询到一条关系的 `pg_id = 42`
- **THEN** 可通过该 ID 在 PostgreSQL 的 `concept_relation` 表中查询到完整的追溯信息（包含 ext_info）

### Requirement: Concept 间关系唯一性

同一对 Concept 节点之间的同类型关系 MUST 保持唯一。

同步时使用 Cypher MERGE 确保幂等：对同一 `(source_code, target_code, relation_type)` 组合，重复同步 MUST 更新属性而非创建重复关系。

#### Scenario: MERGE 保证幂等

- **WHEN** 对同一对概念的同类型关系执行两次同步
- **THEN** Neo4j 中仅存在一条该关系，属性为最新一次同步的值

#### Scenario: 同一对概念可有不同类型关系

- **WHEN** "锂电池" 与 "新能源车" 之间有 `IS_UPSTREAM_OF` 和 `ENABLER_FOR` 两种关系
- **THEN** Neo4j 中 MUST 存在两条不同类型的关系

### Requirement: 枚举定义与关系类型映射

系统 MUST 在 `knowledge_center/domain/model/enums.py` 中维护 `ConceptRelationType` 枚举，其值 MUST 与 Neo4j 中的关系类型名称一一对应。

同步逻辑 MUST 基于该枚举进行关系类型映射，确保 PostgreSQL 中的 `relation_type` 字段值与 Neo4j 关系类型严格一致。

#### Scenario: 枚举值与 Neo4j 关系类型一致

- **WHEN** `ConceptRelationType.IS_UPSTREAM_OF.value` 为 `"IS_UPSTREAM_OF"`
- **THEN** Neo4j 中创建的关系类型名称 MUST 为 `IS_UPSTREAM_OF`
