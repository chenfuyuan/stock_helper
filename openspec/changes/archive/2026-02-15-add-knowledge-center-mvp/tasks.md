## 1. Docker 基础设施与环境配置

- [x] 1.1 `docker-compose.yml` 新增 `neo4j` 服务（`neo4j:5-community`），配置端口 7474/7687、数据卷 `neo4j_data`/`neo4j_logs`、健康检查、加入 `stock_helper_net`
- [x] 1.2 `docker-compose.yml` `app` 服务新增 `depends_on: neo4j: condition: service_healthy`
- [x] 1.3 `docker-compose.yml` `volumes` 部分新增 `neo4j_data` 和 `neo4j_logs`
- [x] 1.4 `.env.example` 新增 `NEO4J_URI`、`NEO4J_USER`、`NEO4J_PASSWORD` 配置项
- [x] 1.5 `requirements.txt` 新增 `neo4j` Python 驱动包
- [x] 1.6 验证：`docker compose up -d` 启动后 Neo4j 健康检查通过，Neo4j Browser（localhost:7474）可访问

## 2. 模块骨架创建

- [x] 2.1 创建 `src/modules/knowledge_center/` 目录结构（domain/model、domain/ports、domain/dtos、domain/exceptions.py、application/services、application/commands、application/queries、application/dtos、infrastructure/persistence、infrastructure/adapters、infrastructure/config.py、presentation/rest）
- [x] 2.2 创建各层 `__init__.py`，确保包可导入
- [x] 2.3 创建 `domain/model/enums.py`：定义 `NodeLabel`（STOCK/INDUSTRY/AREA/MARKET/EXCHANGE）和 `RelationshipType`（BELONGS_TO_INDUSTRY/LOCATED_IN/TRADES_ON/LISTED_ON）枚举

## 3. Domain 层 — 模型与 Port 定义

- [x] 3.1 创建 `domain/model/graph_node.py`：定义 `StockNode`、`IndustryNode`、`AreaNode`、`MarketNode`、`ExchangeNode` Pydantic 实体
- [x] 3.2 创建 `domain/model/graph_relationship.py`：定义关系值对象（source_code、target_name、relationship_type）
- [x] 3.3 创建 `domain/dtos/graph_sync_dtos.py`：定义 `StockGraphSyncDTO`（同步输入 DTO，含股票基本信息 + 维度字段 + 可选财务快照）、`SyncResult`（成功/失败数、耗时）
- [x] 3.4 创建 `domain/dtos/graph_query_dtos.py`：定义 `StockNeighborDTO`、`StockGraphDTO`（含节点列表和关系列表）
- [x] 3.5 创建 `domain/ports/graph_repository.py`：定义 `GraphRepository` ABC，含 `merge_stocks`、`merge_dimensions`、`find_neighbors`、`find_stock_graph`、`ensure_constraints` 方法
- [x] 3.6 创建 `domain/exceptions.py`：定义 `GraphSyncError`、`GraphQueryError` 等领域异常（继承 `AppException`）

## 4. Infrastructure 层 — Neo4j 连接与 Repository 实现

- [x] 4.1 创建 `infrastructure/config.py`：定义 `Neo4jConfig`（BaseSettings，读取 NEO4J_URI/USER/PASSWORD 环境变量）
- [x] 4.2 创建 `infrastructure/persistence/neo4j_driver_factory.py`：Neo4j Driver 工厂函数（`create_neo4j_driver(config) -> Driver`）
- [x] 4.3 创建 `infrastructure/persistence/neo4j_graph_repository.py`：实现 `GraphRepository` 接口
  - 实现 `ensure_constraints()`：CREATE CONSTRAINT IF NOT EXISTS 创建 5 个唯一约束
  - 实现 `merge_stocks()`：UNWIND + MERGE 批量写入 Stock 节点、维度节点及关系
  - 实现 `merge_dimensions()`：批量 MERGE 维度节点
  - 实现 `find_neighbors()`：Cypher MATCH 查询同维度股票
  - 实现 `find_stock_graph()`：Cypher MATCH 查询个股关系网络（depth=1）
- [x] 4.4 验证：编写单元测试 mock Neo4j Session，验证 Cypher 语句生成正确

## 5. Infrastructure 层 — 跨模块 Adapter

- [x] 5.1 创建 `infrastructure/adapters/data_engineering_adapter.py`：从 data_engineering 的 StockRepo/FinancialRepo Port 读取数据，转换为 `StockGraphSyncDTO` 列表
- [x] 5.2 验证：Adapter 返回的 DTO 不包含对 data_engineering 类型的直接引用

## 6. Application 层 — 同步命令与查询用例

- [x] 6.1 创建 `application/commands/sync_graph_command.py`：实现 `SyncGraphCommand`，编排全量/增量同步流程（读源数据 → Adapter 转换 → GraphRepository 写入）
- [x] 6.2 实现同步错误容错：单条失败记日志不中断，完成后返回 `SyncResult` 摘要
- [x] 6.3 实现批量大小可配置（默认 500），通过 UNWIND 分批提交
- [x] 6.4 创建 `application/queries/get_stock_neighbors.py`：调用 `GraphRepository.find_neighbors` 实现同维度查询
- [x] 6.5 创建 `application/queries/get_stock_graph.py`：调用 `GraphRepository.find_stock_graph` 实现关系网络查询
- [x] 6.6 创建 `application/services/graph_service.py`：`GraphService` 作为门面，依赖注入 `GraphRepository`，聚合同步与查询能力
- [x] 6.7 创建 `application/dtos/graph_api_dtos.py`：定义 REST 层使用的响应 DTO

## 7. Presentation 层 — REST API

- [x] 7.1 创建 `presentation/rest/graph_router.py`：定义 FastAPI Router，前缀 `/api/v1/knowledge-graph`
- [x] 7.2 实现 `GET /stocks/{third_code}/neighbors` 端点（参数：dimension、limit）
- [x] 7.3 实现 `GET /stocks/{third_code}/graph` 端点（参数：depth）
- [x] 7.4 实现 `POST /sync` 端点（body：mode、third_codes）
- [x] 7.5 在主应用（`src/main.py`）中注册 `graph_router`

## 8. 依赖注入注册

- [x] 8.1 在 DI 容器中注册 `Neo4jConfig`、Neo4j Driver 工厂
- [x] 8.2 在 DI 容器中注册 `Neo4jGraphRepository` → `GraphRepository` Port 绑定
- [x] 8.3 在 DI 容器中注册 `DataEngineeringAdapter`
- [x] 8.4 在 DI 容器中注册 `GraphService`、`SyncGraphCommand` 及各 Query 用例
- [x] 8.5 验证：应用启动时自动调用 `ensure_constraints()` 创建 Neo4j Schema 约束

## 9. 测试

- [x] 9.1 图谱 Schema 约束测试：验证 5 个唯一约束正确创建（幂等）
- [x] 9.2 全量同步测试：验证 Stock 节点数 = 源数据数，维度节点和关系正确建立
- [x] 9.3 增量同步测试：验证仅同步指定股票，其他数据不变
- [x] 9.4 同步幂等性测试：重复同步后节点数不增加
- [x] 9.5 同步错误容错测试：模拟单条失败，验证不中断且结果摘要正确
- [x] 9.6 查询同维度股票测试：验证各维度（industry/area/market/exchange）返回正确结果
- [x] 9.7 查询个股关系网络测试：验证返回完整关系图且缺失维度不报错
- [x] 9.8 REST API 测试：验证各端点的正常响应和参数校验（422）
- [x] 9.9 财务快照同步测试：验证 Stock 节点财务属性反映最新一期数据

## 10. 接口验证

- [x] 10.1 环境验证：Docker 服务正常启动，Neo4j 健康检查通过
- [x] 10.2 API 路由验证：知识图谱路由正确注册到主应用
- [x] 10.3 同步接口验证：全量/增量同步功能正常，数据正确写入 Neo4j
- [x] 10.4 查询接口验证：同维度股票查询和个股关系网络查询正常返回结果
- [x] 10.5 数据完整性验证：Neo4j 中包含 50+ 股票节点，关系正确建立
- [x] 10.6 测试套件验证：所有 20 个测试用例通过，覆盖核心功能
- [x] 10.7 错误处理验证：API 参数校验、异常处理正常工作
