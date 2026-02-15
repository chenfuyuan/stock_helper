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

#### Scenario: 查询上游产业链

- **WHEN** 查询概念 `BK0003`（新能源车）的上游链路，最大深度 3
- **THEN** 返回从 `BK0003` 出发，沿 `IS_UPSTREAM_OF` 反向追溯的路径
- **THEN** 路径深度不超过 3 层
- **THEN** 结果 MUST 按深度排序，显示每一步的概念和关系

#### Scenario: 查询下游产业链

- **WHEN** 查询概念 `BK0001`（锂电池）的下游链路，最大深度 2
- **THEN** 返回从 `BK0001` 出发，沿 `IS_DOWNSTREAM_OF` 正向追溯的路径
- **THEN** 路径深度不超过 2 层
- **THEN** 结果 MUST 包含所有可达的概念

#### Scenario: 链路去重

- **WHEN** 查询过程中遇到循环依赖（如 A→B→C→A）
- **THEN** MUST 避免无限循环，已访问的概念不再重复访问
- **THEN** 返回的路径 MUST 不包含重复的概念

#### Scenario: 深度限制

- **WHEN** 设置 `max_depth=2`
- **THEN** 查询结果 MUST 不超过 2 层关系
- **THEN** 超过深度限制的路径 MUST 被截断

### Requirement: 概念关系网络可视化支持

系统 SHALL 提供概念关系网络的可视化查询支持，便于前端渲染图谱。

#### Scenario: 获取概念关系网络数据

- **WHEN** 请求概念 `BK0001` 的关系网络数据
- **THEN** 返回适合图谱可视化的数据结构：
  - 节点列表：包含概念代码、名称、类型等属性
  - 边列表：包含关系类型、方向、置信度等属性
- **THEN** 数据格式 MUST 为 JSON，便于前端图库使用

#### Scenario: 支持多概念网络查询

- **WHEN** 请求多个概念的关系网络
- **THEN** 返回这些概念及其直接关系的完整子图
- **THEN** 子图 MUST 包含所有相关的节点和边

### Requirement: REST API — 查询概念关系

系统 SHALL 提供 REST 端点：

```
GET /api/v1/knowledge-graph/concepts/{concept_code}/relations
```

查询参数：

- `direction`（可选，默认 `"outgoing"`）：`"outgoing"` 或 `"incoming"`
- `relation_types`（可选）：关系类型列表，逗号分隔

#### Scenario: 查询概念的出向关系

- **WHEN** 发送 `GET /api/v1/knowledge-graph/concepts/BK0001/relations`
- **THEN** 返回 BK0001 的所有出向关系
- **THEN** 每条关系包含目标概念、关系类型、置信度等

#### Scenario: 查询概念的入向关系

- **WHEN** 发送 `GET /api/v1/knowledge-graph/concepts/BK0001/relations?direction=incoming`
- **THEN** 返回 BK0001 的所有入向关系
- **THEN** 每条关系包含源概念、关系类型、置信度等

#### Scenario: 按关系类型筛选

- **WHEN** 发送 `GET /api/v1/knowledge-graph/concepts/BK0001/relations?relation_types=IS_UPSTREAM_OF,IS_DOWNSTREAM_OF`
- **THEN** 仅返回指定类型的关系

### Requirement: REST API — 查询产业链路径

系统 SHALL 提供 REST 端点：

```
GET /api/v1/knowledge-graph/concepts/{concept_code}/chain
```

查询参数：

- `direction`（可选，默认 `"outgoing"`）：`"outgoing"` 或 `"incoming"`
- `max_depth`（可选，默认 3）：最大路径深度

#### Scenario: 查询上游产业链路径

- **WHEN** 发送 `GET /api/v1/knowledge-graph/concepts/BK0003/chain?direction=incoming&max_depth=2`
- **THEN** 返回 BK0003 的上游产业链路径
- **THEN** 路径深度不超过 2 层
- **THEN** 结果包含每步的概念和关系类型

#### Scenario: 查询下游产业链路径

- **WHEN** 发送 `GET /api/v1/knowledge-graph/concepts/BK0001/chain?direction=outgoing&max_depth=3`
- **THEN** 返回 BK0001 的下游产业链路径
- **THEN** 路径深度不超过 3 层
- **THEN** 结果包含所有可达的概念

#### Scenario: 路径数据结构

- **WHEN** 查询产业链路径
- **THEN** 返回的数据结构 MUST 包含：
  - `concept_code`：起始概念代码
  - `direction`：查询方向
  - `max_depth`：最大深度
  - `nodes`：节点列表，包含概念信息和深度
  - `total_nodes`：节点总数

### Requirement: 性能优化

系统 MUST 优化概念关系查询性能，支持大规模数据集。

#### Scenario: 查询响应时间

- **WHEN** 查询一个有 1000+ 直接关系的概念
- **THEN** 查询响应时间 MUST 在 1 秒内
- **THEN** MUST 使用 Neo4j 索引优化查询性能

#### Scenario: 批量查询优化

- **WHEN** 同时查询多个概念的关系
- **THEN** MUST 使用批量查询减少数据库调用次数
- **THEN** 总响应时间 MUST 在合理范围内

### Requirement: DI Container 注册

`KnowledgeCenterContainer` MUST 注册以下新增组件：

- `GraphService` 或 `ConceptRelationService`（提供查询服务）

#### Scenario: 服务可注入

- **WHEN** 通过 DI 容器请求关系查询服务
- **THEN** MUST 返回已注入 Neo4j 驱动的服务实例
