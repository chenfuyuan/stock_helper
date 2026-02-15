# Purpose

提供概念关系网络的查询能力，支持查询指定概念的关联关系、上下游链路及产业链路径遍历。

## ADDED Requirements

### Requirement: 查询指定概念的直接关系

系统 SHALL 通过 `GraphService`（或新增的 `ConceptRelationService`）提供查询指定概念的所有直接关系的能力。

查询结果 MUST 返回关系列表，每条记录包含：

- `relation_type`（str）：关系类型
- `direction`（str）：关系方向（`outgoing` / `incoming`）
- `related_concept_code`（str）：关联概念代码
- `related_concept_name`（str）：关联概念名称
- `confidence`（float）：置信度
- `source_type`（str）：来源类型

结果 MUST 支持按 `relation_type` 筛选。

#### Scenario: 查询概念的所有直接关系

- **WHEN** 查询概念 `BK0001`（锂电池）的直接关系
- **THEN** 返回该概念作为源或目标的所有关系
- **THEN** 每条结果 MUST 包含关系类型、方向、关联概念信息

#### Scenario: 按关系类型筛选

- **WHEN** 查询概念 `BK0001` 的直接关系，筛选 `relation_type = IS_UPSTREAM_OF`
- **THEN** 仅返回 `IS_UPSTREAM_OF` 类型的关系

#### Scenario: 概念无关系时返回空列表

- **WHEN** 查询一个没有任何关系的概念
- **THEN** 返回空列表，不抛出异常

#### Scenario: 概念不存在时返回空列表

- **WHEN** 查询一个不存在的概念代码
- **THEN** 返回空列表，不抛出异常

### Requirement: 查询概念的上下游链路

系统 SHALL 提供查询指定概念的上下游产业链路径的能力。

查询 MUST 支持 `direction` 参数：

- `upstream`：沿 `IS_UPSTREAM_OF` 方向向上追溯
- `downstream`：沿 `IS_DOWNSTREAM_OF` 方向向下追溯
- `both`：双向查询

查询 MUST 支持 `max_depth` 参数（默认 3），限制遍历深度。

返回结果 MUST 为有序的链路节点列表，包含层级信息。

#### Scenario: 查询上游链路

- **WHEN** 查询概念"新能源车"的上游链路，`max_depth = 2`
- **THEN** 返回沿 `IS_UPSTREAM_OF` 关系追溯的概念列表（如"锂电池" → "锂矿"）
- **THEN** 每个节点 MUST 包含 `depth` 层级信息

#### Scenario: 查询下游链路

- **WHEN** 查询概念"锂电池"的下游链路
- **THEN** 返回沿 `IS_DOWNSTREAM_OF` 关系追溯的概念列表

#### Scenario: 链路深度超过 max_depth 时截断

- **WHEN** 实际链路深度为 5，`max_depth = 3`
- **THEN** 返回结果最深为第 3 层，不继续遍历

#### Scenario: 无上下游关系时返回空

- **WHEN** 查询一个没有上下游关系的概念
- **THEN** 返回空列表

### Requirement: IGraphRepository 扩展概念关系查询方法

`IGraphRepository` 接口 MUST 新增以下方法：

- `find_concept_relations(concept_code: str, relation_type: ConceptRelationType | None = None) -> list[ConceptRelationQueryDTO]`：查询指定概念的直接关系
- `find_concept_chain(concept_code: str, direction: str, max_depth: int) -> list[ConceptChainNodeDTO]`：查询概念的上下游链路

#### Scenario: find_concept_relations 查询双向关系

- **WHEN** 调用 `find_concept_relations("BK0001")`
- **THEN** 返回 `BK0001` 作为源端或目标端的所有关系

#### Scenario: find_concept_chain 遍历链路

- **WHEN** 调用 `find_concept_chain("BK0001", direction="downstream", max_depth=3)`
- **THEN** 返回从 `BK0001` 出发、沿下游方向最多遍历 3 层的所有概念节点

### Requirement: ConceptRelationQueryDTO 定义

系统 MUST 在 `knowledge_center/domain/dtos/concept_relation_query_dtos.py` 中定义查询相关 DTO。

`ConceptRelationQueryDTO` MUST 包含：

- `relation_type`（str）
- `direction`（str）：`outgoing` / `incoming`
- `related_concept_code`（str）
- `related_concept_name`（str）
- `confidence`（float）
- `source_type`（str）

`ConceptChainNodeDTO` MUST 包含：

- `concept_code`（str）
- `concept_name`（str）
- `depth`（int）：距起始概念的层级
- `relation_type`（str）：与上一层的关系类型

#### Scenario: DTO 字段完整

- **WHEN** 查询概念关系并转换为 DTO
- **THEN** 所有字段 MUST 非 None

### Requirement: REST API — 查询概念关系网络

系统 SHALL 提供 REST 端点：

```
GET /api/v1/knowledge-graph/concepts/{code}/relations
```

查询参数：

- `relation_type`（可选）：按关系类型筛选

#### Scenario: 查询概念关系返回 200

- **WHEN** 发送 `GET /api/v1/knowledge-graph/concepts/BK0001/relations`
- **THEN** 返回 HTTP 200 及该概念的所有直接关系列表

#### Scenario: 筛选关系类型

- **WHEN** 发送 `GET /api/v1/knowledge-graph/concepts/BK0001/relations?relation_type=IS_UPSTREAM_OF`
- **THEN** 仅返回 `IS_UPSTREAM_OF` 类型的关系

### Requirement: REST API — 查询产业链路径

系统 SHALL 提供 REST 端点：

```
GET /api/v1/knowledge-graph/concepts/{code}/chain
```

查询参数：

- `direction`（必填）：`upstream` / `downstream` / `both`
- `max_depth`（可选，默认 3）

#### Scenario: 查询上游链路返回 200

- **WHEN** 发送 `GET /api/v1/knowledge-graph/concepts/BK0001/chain?direction=upstream`
- **THEN** 返回 HTTP 200 及上游链路节点列表

#### Scenario: 查询双向链路

- **WHEN** 发送 `GET /api/v1/knowledge-graph/concepts/BK0001/chain?direction=both&max_depth=2`
- **THEN** 返回 HTTP 200 及上下游双向链路节点列表

#### Scenario: 缺少 direction 参数返回 422

- **WHEN** 发送 `GET /api/v1/knowledge-graph/concepts/BK0001/chain`（无 direction）
- **THEN** 返回 HTTP 422
