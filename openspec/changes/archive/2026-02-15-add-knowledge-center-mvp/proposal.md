## Why

系统已积累丰富的结构化数据（股票基本信息、日线行情、财务报表、披露公告），但这些数据以关系表形式孤立存储在 PostgreSQL 中，缺乏**实体间关联关系**的显式建模能力。Research 模块的多类专家在分析个股时，无法高效获取"同行业竞品对比""同地域上市公司聚类""产业链上下游"等关系型洞察。引入 Neo4j 知识图谱作为支撑能力层的知识中心，可以将离散数据编织为关联网络，为后续的智能推理（如关联风险传导、板块联动分析）奠定基础。

## What Changes

- **新增 `knowledge_center` 模块**（`src/modules/knowledge_center/`）：按 DDD 分层创建完整模块骨架（Domain / Application / Infrastructure / Presentation）。
- **Docker 基础设施变更**：
  - `docker-compose.yml` 新增 `neo4j` 服务（`neo4j:5-community`），配置端口映射（7474 / 7687）、数据卷持久化、健康检查，并加入 `stock_helper_net` 网络。
  - `app` 服务新增 `depends_on: neo4j` 确保启动顺序。
  - `.env` / `.env.example` 新增 Neo4j 连接配置项（`NEO4J_URI`、`NEO4J_USER`、`NEO4J_PASSWORD`）。
  - `requirements.txt` 新增 `neo4j` Python 驱动依赖。
- **新增 Neo4j 部署文档**（`docs/neo4j-deployment.md`）：覆盖本地开发环境搭建、环境变量配置、数据卷管理、Neo4j Browser 访问、常见问题排查。
- **定义图谱数据模型**：建立以 Stock 为核心节点，关联 Industry（行业）、Area（地域）、Market（市场）、Exchange（交易所）等维度节点的图谱 Schema，并将财务快照与行情快照作为节点属性或关联边。
- **实现数据同步管道**：从 `data_engineering` 模块读取现有数据（通过 Ports），批量写入 Neo4j 图谱，支持全量初始化与增量更新。
- **暴露图谱查询能力**：通过 `GraphRepository`（Port）和 `GraphService`（Application Service）对外提供关系查询 API（如：查询同行业股票、获取个股关联图谱等）。

## Capabilities

### New Capabilities

- `knowledge-graph-schema`: 图谱数据模型定义——节点类型（Stock / Industry / Area / Market / Exchange）、关系类型（BELONGS_TO_INDUSTRY / LOCATED_IN / LISTED_ON 等）、属性规范与约束。
- `knowledge-graph-sync`: 数据同步管道——从 `data_engineering` 模块消费 StockInfo / StockFinance / StockDaily 数据，经 DTO 转换后批量写入 Neo4j，支持全量与增量两种模式。
- `knowledge-graph-query`: 图谱查询服务——通过 `GraphRepository` Port 和 `GraphService` 对外暴露关系查询能力（同行业股票、个股关系网络、多维筛选等），并提供 REST API。

### Modified Capabilities

（无。本次为全新模块，不修改现有能力的需求定义。）

## Impact

- **新增依赖**：`neo4j` Python 驱动（`neo4j` 包）；Docker Compose 新增 Neo4j 服务（`neo4j:5-community`）。
- **受影响文件**：
  - `docker-compose.yml`：新增 `neo4j` 服务、数据卷 `neo4j_data`；`app` 服务新增依赖。
  - `.env` / `.env.example`：新增 `NEO4J_URI`、`NEO4J_USER`、`NEO4J_PASSWORD` 配置项。
  - `requirements.txt`：新增 `neo4j` 包。
  - `src/shared/`：可能需增加 Neo4j Driver 工厂或连接管理基础设施。
  - DI 容器：需注册 `knowledge_center` 模块的服务与端口实现。
- **新增文档**：`docs/neo4j-deployment.md`（本地开发环境搭建与运维指引）。
- **跨模块依赖**：`knowledge_center` 依赖 `data_engineering` 的数据查询能力（通过已有的 `StockRepo` / `FinancialRepo` Ports），遵循支撑层间通信规则。
- **API 变更**：新增 REST 端点（`/api/v1/knowledge-graph/...`），不影响现有 API。
- **验证方式**：通过自动化测试覆盖图谱 Schema 约束、同步正确性、查询结果准确性三个场景。
