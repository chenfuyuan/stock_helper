# Purpose

扩展知识图谱查询能力，支持概念题材维度。

## MODIFIED Requirements

### Requirement: 查询同维度股票（Neighbors）

系统 SHALL 通过 `GraphService` 提供查询与指定股票共享同一维度节点的其他股票的能力。

支持的维度 MUST 包含：`industry`、`area`、`market`、`exchange`、`concept`。

查询结果 MUST 返回邻居股票列表，每条记录至少包含：`third_code`、`name`、`industry`（若查询维度为 industry 则为该行业名）。

当 `dimension = "concept"` 时，查询 MUST 额外要求 `dimension_name` 参数指定概念名称（因为一只股票可属于多个概念，需明确查询哪个概念的同概念股），返回该概念下的其他成份股。

结果 MUST 支持 `limit` 参数限制返回数量，默认值为 20。

#### Scenario: 查询同行业股票

- **WHEN** 查询 `third_code = "000001.SZ"`、`dimension = "industry"` 的邻居
- **THEN** 返回与 "000001.SZ" 属于同一行业的其他 Stock 列表
- **THEN** 结果 MUST NOT 包含查询股票自身（"000001.SZ"）

#### Scenario: 查询同地区股票

- **WHEN** 查询 `third_code = "000001.SZ"`、`dimension = "area"` 的邻居
- **THEN** 返回与 "000001.SZ" 位于同一地域的其他 Stock 列表

#### Scenario: 查询同概念股票

- **WHEN** 查询 `third_code = "000001.SZ"`、`dimension = "concept"`、`dimension_name = "低空经济"` 的邻居
- **THEN** 返回与 "000001.SZ" 同属于"低空经济"概念的其他 Stock 列表
- **THEN** 结果 MUST NOT 包含查询股票自身

#### Scenario: 概念维度缺少 dimension_name

- **WHEN** 查询 `dimension = "concept"` 但未提供 `dimension_name`
- **THEN** MUST 返回参数校验错误（HTTP 422 或领域异常）

#### Scenario: 股票不存在时返回空

- **WHEN** 查询一个不存在的 `third_code = "999999.XX"` 的邻居
- **THEN** 返回空列表，不抛出异常

#### Scenario: limit 参数生效

- **WHEN** 某行业有 50 支股票，查询时 `limit = 10`
- **THEN** 返回结果最多 10 条

### Requirement: 查询个股关系网络（Graph）

系统 SHALL 提供查询指定股票的完整关系网络能力，返回该股票及其所有直接关联的维度节点和关系。

查询 MUST 支持 `depth` 参数（默认值 1），表示关系遍历深度。MVP 阶段仅需支持 `depth = 1`。

返回结果 MUST 包含：

- 中心 Stock 节点及其属性
- 所有关联的维度节点（Industry / Area / Market / Exchange / **Concept**）
- 连接它们的关系类型

#### Scenario: 查询深度为 1 的关系网络

- **WHEN** 查询 `third_code = "000001.SZ"`、`depth = 1`
- **THEN** 返回结果包含 "000001.SZ" Stock 节点及其关联的 Industry、Area、Market、Exchange、Concept 节点和关系

#### Scenario: 股票属于多个概念

- **WHEN** 股票 "000001.SZ" 属于 3 个概念
- **THEN** 关系网络中 MUST 包含 3 个 Concept 节点及对应的 BELONGS_TO_CONCEPT 关系

#### Scenario: 股票无某维度关系

- **WHEN** 某股票的 `industry` 为 null（无 BELONGS_TO_INDUSTRY 关系）
- **THEN** 返回结果中不包含 Industry 节点，但其他维度关系（包括 Concept）正常返回

#### Scenario: 股票不存在时返回 null

- **WHEN** 查询一个不存在的 `third_code = "999999.XX"` 的关系网络
- **THEN** 返回 null 或空结果，不抛出异常

### Requirement: GraphRepository Port 定义

系统 MUST 在 `knowledge_center/domain/ports/graph_repository.py` 中定义 `GraphRepository` ABC 接口。

该接口 MUST 至少包含以下方法：

- `merge_stocks(stocks: list[StockGraphDTO]) -> SyncResult`：批量写入/更新 Stock 节点及维度关系
- `merge_dimensions(dimensions: list[DimensionDTO]) -> None`：批量写入/更新维度节点
- `merge_concepts(concepts: list[ConceptGraphSyncDTO]) -> SyncResult`：批量写入/更新 Concept 节点及其与 Stock 的关系
- `delete_all_concept_relationships() -> int`：删除所有 BELONGS_TO_CONCEPT 关系
- `find_neighbors(third_code: str, dimension: str, limit: int, dimension_name: str | None = None) -> list[StockNeighborDTO]`：查询同维度股票，`dimension_name` 在 `dimension="concept"` 时必填
- `find_stock_graph(third_code: str, depth: int) -> StockGraphDTO | None`：查询个股关系网络（包含 Concept 节点）
- `ensure_constraints() -> None`：确保图谱唯一约束存在（包含 Concept.code）

#### Scenario: Port 在 Domain 层定义

- **WHEN** 检查 `GraphRepository` 的定义位置
- **THEN** 该 ABC 接口 MUST 位于 `src/modules/knowledge_center/domain/ports/graph_repository.py`
- **THEN** 接口方法的入参和出参 MUST 使用 `domain/dtos/` 中定义的 DTO 类型

### Requirement: REST API — 查询同维度股票

系统 SHALL 提供 REST 端点：

```
GET /api/v1/knowledge-graph/stocks/{third_code}/neighbors?dimension={dimension}&limit={limit}&dimension_name={dimension_name}
```

参数说明：

- `third_code`（路径参数，必填）：股票代码
- `dimension`（查询参数，必填）：维度类型，枚举值 `industry | area | market | exchange | concept`
- `limit`（查询参数，可选）：返回数量上限，默认 20
- `dimension_name`（查询参数，条件必填）：当 `dimension = "concept"` 时 MUST 提供，指定概念名称

#### Scenario: 正常查询返回 200

- **WHEN** 发送 `GET /api/v1/knowledge-graph/stocks/000001.SZ/neighbors?dimension=industry`
- **THEN** 返回 HTTP 200 及 JSON 格式的股票列表

#### Scenario: 查询概念维度返回 200

- **WHEN** 发送 `GET /api/v1/knowledge-graph/stocks/000001.SZ/neighbors?dimension=concept&dimension_name=低空经济`
- **THEN** 返回 HTTP 200 及同属"低空经济"概念的其他股票列表

#### Scenario: 概念维度缺少 dimension_name 返回 422

- **WHEN** 发送 `GET /api/v1/knowledge-graph/stocks/000001.SZ/neighbors?dimension=concept`（无 dimension_name）
- **THEN** 返回 HTTP 422 及错误信息

#### Scenario: 无效维度返回 422

- **WHEN** 发送 `GET /api/v1/knowledge-graph/stocks/000001.SZ/neighbors?dimension=invalid`
- **THEN** 返回 HTTP 422 及错误信息

#### Scenario: 缺少 dimension 参数返回 422

- **WHEN** 发送 `GET /api/v1/knowledge-graph/stocks/000001.SZ/neighbors`（无 dimension）
- **THEN** 返回 HTTP 422

### Requirement: REST API — 查询个股关系网络

系统 SHALL 提供 REST 端点：

```
GET /api/v1/knowledge-graph/stocks/{third_code}/graph?depth={depth}
```

参数说明：

- `third_code`（路径参数，必填）：股票代码
- `depth`（查询参数，可选）：遍历深度，默认 1

#### Scenario: 正常查询返回 200

- **WHEN** 发送 `GET /api/v1/knowledge-graph/stocks/000001.SZ/graph`
- **THEN** 返回 HTTP 200 及 JSON 格式的关系网络数据，包含节点（含 Concept 节点）和关系信息

#### Scenario: 股票不存在返回 200 空结果

- **WHEN** 发送 `GET /api/v1/knowledge-graph/stocks/999999.XX/graph`
- **THEN** 返回 HTTP 200 及 null 或空对象（不返回 404，因为这不是资源不存在，而是图谱中无对应数据）
