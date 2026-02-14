## Why

当前知识图谱仅包含股票基础元数据（行业/地域/市场/交易所），缺乏**概念题材**这一维度。概念题材是市场短期资金流向最直接的映射——它比行业分类更敏捷、能发现跨行业隐性关联（如"华为产业链"横跨电子、通信、汽车），是"投机为矛"策略的关键数据底座。这是知识图谱演进路线（`docs/context/evolution/knowledge_center_roadmap.md`）的**阶段一**，也是后续概念热度监控、板块联动分析等高级能力的前置条件。

由于 Tushare 积分不足（2000 分）无法调用概念板块相关接口，本次使用 **akshare** 作为概念数据源。

## What Changes

- **data_engineering 模块**：新增 akshare 概念数据提供者（Provider Port + 基础设施适配器），提供"概念列表"和"概念成份股"两项数据获取能力。概念数据持久化到 PostgreSQL（`concept` + `concept_stock` 表），与现有股票数据的管理模式一致。这是该模块首次引入 akshare 数据源，与现有 Tushare 数据源并存。
- **knowledge_center 模块**：
  - 图谱 Schema 扩展：新增 `Concept` 节点类型和 `BELONGS_TO_CONCEPT` 关系类型。
  - 同步管道扩展：新增概念数据同步命令，从 data_engineering 的 PostgreSQL 读取概念数据后写入 Neo4j（与股票数据同步模式一致）。
  - 查询能力扩展：现有邻居查询和关系网络查询自然支持概念维度。

**MVP 边界（明确不做）**：
- 不引入关联强度/权重（龙头 vs 跟风）
- 不引入入选理由（reason 属性）
- 不引入概念热度指数（heat_score）
- 不引入概念层级关系（SUB_CONCEPT_OF）

## Capabilities

### New Capabilities

- `concept-data-source`: data_engineering 模块新增 akshare 概念数据能力——定义 `IConceptDataProvider` Port（数据获取）和 `IConceptRepository` Port（持久化），实现 akshare 适配器和 PostgreSQL 仓储，提供概念列表获取、成份股查询和数据持久化能力。

### Modified Capabilities

- `knowledge-graph-schema`: 扩展图谱 Schema，新增 Concept 节点（以 `code` 为唯一约束键）和 `(Stock)-[:BELONGS_TO_CONCEPT]->(Concept)` 关系定义。
- `knowledge-graph-sync`: 扩展同步管道，新增概念数据同步命令，从 data_engineering 概念数据源获取数据并批量写入 Neo4j。
- `knowledge-graph-query`: 扩展查询能力，邻居查询新增 `concept` 维度支持，关系网络查询自然包含 Concept 节点和 BELONGS_TO_CONCEPT 关系。

## Impact

- **data_engineering 模块**：
  - 新增 `domain/ports/providers/concept_data_provider.py`（IConceptDataProvider Port）
  - 新增 `domain/ports/repositories/concept_repo.py`（IConceptRepository Port）
  - 新增 `domain/model/concept.py`（Concept + ConceptStock 实体）
  - 新增 `infrastructure/external_apis/akshare/` 目录（akshare 客户端 + 概念数据转换器）
  - 新增 `infrastructure/persistence/models/concept_model.py`（ORM Model）
  - 新增 `infrastructure/persistence/repositories/pg_concept_repo.py`（PostgreSQL 仓储实现）
  - 新增 Alembic migration（`concept` + `concept_stock` 表）
  - 新增 `application/commands/sync_concept_data_cmd.py`（akshare → PostgreSQL 同步命令）
  - 新增概念相关 DTO（概念列表 DTO、概念成份股 DTO）
  - DI Container 需注册新的 Provider + Repository
- **knowledge_center 模块**：
  - `domain/model/enums.py` 扩展（新增 CONCEPT 节点标签、BELONGS_TO_CONCEPT 关系类型）
  - `domain/model/` 新增 `ConceptNode` 实体
  - `domain/dtos/` 新增概念同步相关 DTO
  - `domain/ports/graph_repository.py` 扩展（新增概念相关 merge/query 方法）
  - `infrastructure/adapters/` 新增概念数据适配器（调用 DE 模块的应用服务查询 PostgreSQL）
  - `infrastructure/persistence/neo4j_graph_repository.py` 扩展（新增 Concept 相关 Cypher 语句）
  - `application/commands/` 新增或扩展概念同步命令
  - `presentation/rest/graph_router.py` 扩展（同步 API 支持概念模式、查询 API 支持概念维度）
- **外部依赖**：新增 `akshare` Python 包依赖
- **验证方式**：通过自动化测试验证概念数据获取、图谱写入和查询场景
