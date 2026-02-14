## ADDED Requirements

### Requirement: 查询同维度股票（Neighbors）

系统 SHALL 通过 `GraphService` 提供查询与指定股票共享同一维度节点的其他股票的能力。

支持的维度 MUST 包含：`industry`、`area`、`market`、`exchange`。

查询结果 MUST 返回邻居股票列表，每条记录至少包含：`third_code`、`name`、`industry`（若查询维度为 industry 则为该行业名）。

结果 MUST 支持 `limit` 参数限制返回数量，默认值为 20。

#### Scenario: 查询同行业股票

- **WHEN** 查询 `third_code = "000001.SZ"`、`dimension = "industry"` 的邻居
- **THEN** 返回与 "000001.SZ" 属于同一行业的其他 Stock 列表
- **THEN** 结果 MUST NOT 包含查询股票自身（"000001.SZ"）

#### Scenario: 查询同地区股票

- **WHEN** 查询 `third_code = "000001.SZ"`、`dimension = "area"` 的邻居
- **THEN** 返回与 "000001.SZ" 位于同一地域的其他 Stock 列表

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
- 所有关联的维度节点（Industry / Area / Market / Exchange）
- 连接它们的关系类型

#### Scenario: 查询深度为 1 的关系网络

- **WHEN** 查询 `third_code = "000001.SZ"`、`depth = 1`
- **THEN** 返回结果包含 "000001.SZ" Stock 节点及其关联的 Industry、Area、Market、Exchange 节点和关系

#### Scenario: 股票无某维度关系

- **WHEN** 某股票的 `industry` 为 null（无 BELONGS_TO_INDUSTRY 关系）
- **THEN** 返回结果中不包含 Industry 节点，但其他维度关系正常返回

#### Scenario: 股票不存在时返回 null

- **WHEN** 查询一个不存在的 `third_code = "999999.XX"` 的关系网络
- **THEN** 返回 null 或空结果，不抛出异常

### Requirement: GraphRepository Port 定义

系统 MUST 在 `knowledge_center/domain/ports/graph_repository.py` 中定义 `GraphRepository` ABC 接口。

该接口 MUST 至少包含以下方法：
- `merge_stocks(stocks: list[StockGraphDTO]) -> SyncResult`：批量写入/更新 Stock 节点及维度关系
- `merge_dimensions(dimensions: list[DimensionDTO]) -> None`：批量写入/更新维度节点
- `find_neighbors(third_code: str, dimension: str, limit: int) -> list[StockNeighborDTO]`：查询同维度股票
- `find_stock_graph(third_code: str, depth: int) -> StockGraphDTO | None`：查询个股关系网络
- `ensure_constraints() -> None`：确保图谱唯一约束存在

#### Scenario: Port 在 Domain 层定义

- **WHEN** 检查 `GraphRepository` 的定义位置
- **THEN** 该 ABC 接口 MUST 位于 `src/modules/knowledge_center/domain/ports/graph_repository.py`
- **THEN** 接口方法的入参和出参 MUST 使用 `domain/dtos/` 中定义的 DTO 类型

### Requirement: GraphService 应用服务

系统 MUST 在 `knowledge_center/application/services/graph_service.py` 中定义 `GraphService`，作为 `knowledge_center` 模块对外暴露的核心应用服务。

`GraphService` MUST 通过依赖注入接收 `GraphRepository` 接口（而非具体实现）。

#### Scenario: GraphService 依赖注入

- **WHEN** 创建 `GraphService` 实例
- **THEN** MUST 通过构造函数注入 `GraphRepository`
- **THEN** 不 MUST 直接依赖 Neo4j 驱动或任何基础设施类

### Requirement: REST API — 查询同维度股票

系统 SHALL 提供 REST 端点：

```
GET /api/v1/knowledge-graph/stocks/{third_code}/neighbors?dimension={dimension}&limit={limit}
```

参数说明：
- `third_code`（路径参数，必填）：股票代码
- `dimension`（查询参数，必填）：维度类型，枚举值 `industry | area | market | exchange`
- `limit`（查询参数，可选）：返回数量上限，默认 20

#### Scenario: 正常查询返回 200

- **WHEN** 发送 `GET /api/v1/knowledge-graph/stocks/000001.SZ/neighbors?dimension=industry`
- **THEN** 返回 HTTP 200 及 JSON 格式的股票列表

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
- **THEN** 返回 HTTP 200 及 JSON 格式的关系网络数据，包含节点和关系信息

#### Scenario: 股票不存在返回 200 空结果

- **WHEN** 发送 `GET /api/v1/knowledge-graph/stocks/999999.XX/graph`
- **THEN** 返回 HTTP 200 及 null 或空对象（不返回 404，因为这不是资源不存在，而是图谱中无对应数据）
