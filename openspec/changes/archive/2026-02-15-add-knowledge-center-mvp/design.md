## Context

系统当前的数据底座（`data_engineering` 模块）将股票基本信息、日线行情、财务报表等结构化数据存储在 PostgreSQL 中。这些数据以表为单位组织，缺乏显式的实体关系建模——例如"股票 A 与股票 B 属于同一行业"这一关系需要通过 SQL JOIN 动态计算，无法直接遍历。

`knowledge_center` 在 `vision-and-modules.md` 中已被定义为支撑能力层模块，路径 `src/modules/knowledge_center/`，对外暴露 `GraphRepository` 和 `GraphService`。本设计将这一规划落地为基于 Neo4j 的 MVP 实现。

当前基础设施：Docker Compose 管理 `app`（FastAPI）+ `db`（PostgreSQL 15），统一在 `stock_helper_net` 桥接网络中。

## Goals / Non-Goals

**Goals:**

- 在 Docker Compose 中引入 Neo4j 5 Community，与现有服务共存，开发者零额外配置即可启动。
- 建立以 Stock 为中心的知识图谱，将 Industry / Area / Market / Exchange 建模为独立维度节点，通过关系边关联。
- 实现从 PostgreSQL（data_engineering）到 Neo4j 的全量与增量同步管道。
- 通过 `GraphRepository` Port 和 `GraphService` 应用服务对外暴露图谱查询能力，提供 REST API。
- 遵循项目 DDD 分层架构与依赖倒置原则，Neo4j 实现细节封装在 Infrastructure 层。

**Non-Goals:**

- 不实现实时流式同步（事件驱动）——MVP 阶段采用批量触发模式，后续可演进为事件驱动。
- 不引入 NLP/LLM 驱动的自动实体抽取——本阶段仅基于已有结构化数据构建图谱。
- 不构建图谱可视化前端——仅通过 REST API 和 Neo4j Browser（开发阶段）查看图谱。
- 不实现复杂的图算法（如 PageRank、社区发现）——MVP 仅支持基础关系查询。
- 不做产业链/供应链关系建模——当前数据中无供应链数据源，留待后续引入。

## Decisions

### D1: 图数据库选型 — Neo4j 5 Community Edition

**选择**：Neo4j 5 Community（Docker 官方镜像 `neo4j:5-community`）。

**替代方案**：
- *ArangoDB*：多模型（文档+图），但团队无使用经验，生态不如 Neo4j 成熟。
- *Amazon Neptune*：托管服务，但项目当前为本地 Docker 部署，引入云依赖增加复杂度。
- *PostgreSQL AGE 插件*：可复用现有 PG，但图查询能力有限，Cypher 支持不完整。

**理由**：Neo4j 是最成熟的原生图数据库，Cypher 查询语言直观强大，Python 驱动稳定，Community 版本对 MVP 功能完全够用，团队学习成本最低。

### D2: 图谱 Schema 设计 — 星型维度模型

**选择**：以 `Stock` 节点为中心的星型拓扑，维度节点包括 `Industry`、`Area`、`Market`、`Exchange`。

```
(Stock)-[:BELONGS_TO_INDUSTRY]->(Industry)
(Stock)-[:LOCATED_IN]->(Area)
(Stock)-[:TRADES_ON]->(Market)
(Stock)-[:LISTED_ON]->(Exchange)
```

**属性设计**：
- **Stock 节点**：`third_code`（唯一约束）、`symbol`、`name`、`fullname`、`list_date`、`list_status`、`curr_type`。财务快照字段（最新一期 `roe`、`roa`、`gross_margin`、`debt_to_assets`、`pe_ttm`、`pb`、`total_mv`）作为节点属性存储，便于单跳查询。
- **维度节点**：`name` 为唯一约束（如 Industry.name = "银行"、Area.name = "深圳"）。

**替代方案**：
- *将财务数据建为独立 FinanceSnapshot 节点*：语义更清晰，但 MVP 阶段增加节点数量与查询复杂度，收益有限。后续可演进。
- *将日线行情也建为节点*：数据量巨大（每天 × 5000+ 股票），不适合 MVP，且图谱不擅长时序查询。

**理由**：星型模型简单直观，维度节点天然支持"同行业""同地区"聚合查询，财务快照作为属性减少关系跳数，适合 MVP 快速验证。

### D3: 模块内部分层

严格遵循项目洋葱架构：

```
src/modules/knowledge_center/
├── domain/
│   ├── model/
│   │   ├── graph_node.py          # Stock / Industry / Area 等领域实体
│   │   ├── graph_relationship.py  # 关系类型枚举与值对象
│   │   └── enums.py               # 图谱相关枚举
│   ├── ports/
│   │   └── graph_repository.py    # GraphRepository ABC
│   ├── dtos/
│   │   ├── graph_query_dtos.py    # 查询入参/出参 DTO
│   │   └── graph_sync_dtos.py     # 同步入参 DTO
│   └── exceptions.py              # 领域异常
├── application/
│   ├── services/
│   │   └── graph_service.py       # GraphService（编排同步与查询）
│   ├── commands/
│   │   └── sync_graph_command.py  # 全量/增量同步命令
│   ├── queries/
│   │   ├── get_stock_neighbors.py # 查询同行业/同地区股票
│   │   └── get_stock_graph.py     # 查询个股关系网络
│   └── dtos/
│       └── graph_api_dtos.py      # REST 层 DTO
├── infrastructure/
│   ├── persistence/
│   │   └── neo4j_graph_repository.py  # GraphRepository 的 Neo4j 实现
│   ├── adapters/
│   │   └── data_engineering_adapter.py # 从 data_engineering 读取数据的适配器
│   └── config.py                       # Neo4j 连接配置
└── presentation/
    └── rest/
        └── graph_router.py            # FastAPI 路由
```

### D4: Neo4j 连接管理

**选择**：在 `knowledge_center/infrastructure/config.py` 中创建模块级 Neo4j Driver 工厂，通过 DI 注入。

```python
# 伪代码
class Neo4jConfig(BaseSettings):
    neo4j_uri: str
    neo4j_user: str
    neo4j_password: str

def create_neo4j_driver(config: Neo4jConfig) -> neo4j.Driver:
    return GraphDatabase.driver(config.neo4j_uri, auth=(config.neo4j_user, config.neo4j_password))
```

**替代方案**：将 Neo4j Driver 放在 `src/shared/infrastructure/`。

**理由**：当前只有 `knowledge_center` 使用 Neo4j，放在模块内部符合"最小暴露"原则。若将来其他模块也需要图数据库，再提升到 Shared Kernel。

### D5: 数据同步策略

**选择**：应用层 Command（`SyncGraphCommand`）编排同步流程：

1. 通过 `data_engineering` 的 Port（如 `StockRepo`）查询源数据。
2. 跨模块数据通过 Adapter 转换为本模块 `domain/dtos/` 中的 `GraphSyncDTO`。
3. 调用 `GraphRepository.merge_stocks()`、`merge_dimensions()` 等方法批量写入 Neo4j。
4. 使用 Cypher `MERGE` 语句确保幂等性（重复执行不产生重复数据）。

**全量 vs 增量**：
- **全量同步**：遍历所有 StockInfo 记录，MERGE 全部节点与关系。适用于首次初始化或数据校正。
- **增量同步**：基于 `last_finance_sync_date` 或指定时间窗口，仅同步变更的股票。适用于日常更新。

**批量写入**：使用 `UNWIND + MERGE` 批量提交（每批 500-1000 条），避免逐条写入的性能问题。可选使用 APOC 的 `apoc.periodic.iterate` 进一步优化。

### D6: REST API 设计

```
GET  /api/v1/knowledge-graph/stocks/{third_code}/neighbors
     ?dimension=industry|area|market|exchange
     &limit=20

GET  /api/v1/knowledge-graph/stocks/{third_code}/graph
     ?depth=1

POST /api/v1/knowledge-graph/sync
     Body: { "mode": "full" | "incremental", "third_codes": [...] }
```

## Risks / Trade-offs

**[R1] Neo4j Community 版本无集群能力** → MVP 阶段单节点足够；若未来需要高可用，可升级到 Enterprise 或切换到 Neo4j AuraDB。数据始终可从 PostgreSQL 全量重建。

**[R2] 图谱数据与 PostgreSQL 数据的一致性** → 图谱为 PostgreSQL 的只读派生视图，非 SSOT（Single Source of Truth）。若出现不一致，以 PostgreSQL 数据为准，通过全量同步修复。

**[R3] 财务快照作为 Stock 节点属性可能导致属性膨胀** → MVP 仅保留最新一期核心财务指标（约 6-8 个字段），不保留历史。后续如需历史对比，再引入 FinanceSnapshot 节点。

**[R4] 同步管道与 data_engineering 的耦合** → 通过 Adapter + DTO 隔离，`knowledge_center` Domain 层不直接依赖 `data_engineering` 的任何类型。Adapter 层变更不影响 Domain。

**[R5] 首次全量同步可能较慢** → 约 5000+ 股票 × 4 类关系，预计万级 MERGE 操作。使用批量写入 + UNWIND 控制在分钟级别完成。可接受。
