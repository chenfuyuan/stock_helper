## MODIFIED Requirements

### Requirement: 图谱查询响应格式
图谱查询接口 SHALL 返回统一的 `BaseResponse[T]` 格式，确保与其他 API 接口响应格式的一致性。

#### Scenario: 查询同维度股票响应
- **WHEN** 查询同维度股票请求成功完成
- **THEN** 系统返回 `BaseResponse[list[StockNeighborResponse]]`，其中：
  - `success: true`
  - `message: "同维度股票查询成功"`
  - `code: "STOCK_NEIGHBORS_SUCCESS"`
  - `data: list[StockNeighborResponse]` 包含同维度股票列表

#### Scenario: 查询个股关系网络响应
- **WHEN** 查询个股关系网络请求成功完成
- **THEN** 系统返回 `BaseResponse[StockGraphResponse | None]`，其中：
  - `success: true`
  - `message: "个股关系网络查询成功"`
  - `code: "STOCK_GRAPH_SUCCESS"`
  - `data: StockGraphResponse | None` 包含图谱数据或 null

#### Scenario: 同步图谱数据响应
- **WHEN** 同步图谱数据请求完成
- **THEN** 系统返回 `BaseResponse[SyncGraphResponse]`，其中：
  - `success: true`
  - `message: "图谱数据同步成功"`
  - `code: "GRAPH_SYNC_SUCCESS"`
  - `data: SyncGraphResponse` 包含同步结果统计

#### Scenario: 图谱操作失败响应
- **WHEN** 图谱操作过程中发生错误
- **THEN** 系统返回 `ErrorResponse`，包含：
  - `success: false`
  - `message: str` 图谱操作失败的具体描述
  - `code: str` 对应的错误代码（如 "STOCK_NOT_FOUND"、"GRAPH_SYNC_ERROR" 等）
