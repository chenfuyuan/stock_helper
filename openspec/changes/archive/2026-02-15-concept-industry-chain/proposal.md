## Why

当前知识图谱中的 `Concept` 节点彼此孤立，仅通过 `BELONGS_TO_CONCEPT` 关系连接到 `Stock`，是一组扁平的"标签"。这无法支撑产业链分析、主题轮动追踪、上下游风险传导等高价值场景。将"概念点集合"升级为"概念关系网络"，是图谱从信息检索工具走向结构化推理引擎的关键一步。

## What Changes

- **新增 Concept 间关系类型**：在 Neo4j 图谱中引入 Concept 节点之间的定向关系，支持 `IS_UPSTREAM_OF`（上游）、`IS_DOWNSTREAM_OF`（下游）、`COMPETES_WITH`（竞争）、`IS_PART_OF`（组成部分）、`ENABLER_FOR`（技术驱动）等语义关系。
- **新增 PostgreSQL 概念关系记录表**：作为概念关系的**唯一主数据存储（Single Source of Truth）**，Neo4j 仅为查询加速的派生视图。即使 Neo4j 图谱被删除，也可完全从 PostgreSQL 数据重建。表中记录关系的创建来源（手动 / LLM 推荐）、确认状态、置信度等结构化字段，并通过 `ext_info`（JSONB）字段存储完整的追溯上下文（如 LLM 的输入 prompt、原始输出、分析结果、推理依据、模型版本等），确保每条关系的来龙去脉可追溯。
- **新增手动管理 API**：提供 REST 端点，支持用户手动创建、查询、更新、删除概念间关系。
- **新增 LLM 辅助分析能力**：利用 `llm_platform` 模块分析给定概念集合，自动推荐概念间关系及其类型，推荐结果写入 PostgreSQL 待确认。
- **新增概念关系同步到 Neo4j**：将 PostgreSQL 中已确认的概念关系同步到 Neo4j，构建概念关系网络。Neo4j 为派生视图，可随时从 PostgreSQL 全量重建。
- **新增概念关系网络查询**：提供 API 查询指定概念的上下游链路及关联概念网络。

## Capabilities

### New Capabilities

- `concept-relation-management`：概念间关系的手动 CRUD 管理。PostgreSQL 为 Single Source of Truth（即使 Neo4j 删除也可重建）。持久化包含结构化审计字段 + `ext_info`（JSONB）追溯上下文。提供 REST API 端点，支持关系的完整生命周期管理（创建、查询、更新、删除）。
- `concept-relation-llm-suggest`：基于 LLM 的概念关系自动推荐能力。给定一组概念，调用 `llm_platform` 分析并输出推荐的关系列表（含关系类型、置信度、推理依据）。结果写入 PostgreSQL 待人工确认，`ext_info` 中完整记录 LLM 输入 prompt、原始输出、解析后的分析结果、推理依据、模型版本等信息。
- `concept-relation-graph-sync`：将 PostgreSQL 中已确认的概念关系同步到 Neo4j 图谱，构建 Concept 间的关系网络。Neo4j 为派生查询视图，支持从 PostgreSQL 全量重建。
- `concept-relation-graph-query`：提供概念关系网络的查询能力，支持查询指定概念的上下游链路、关联概念、以及产业链路径遍历。

### Modified Capabilities

- `knowledge-graph-schema`：新增 Concept 节点间的关系类型定义（`IS_UPSTREAM_OF`、`IS_DOWNSTREAM_OF`、`COMPETES_WITH`、`IS_PART_OF`、`ENABLER_FOR`），以及关系上的属性（来源、置信度等）。

## Impact

- **knowledge_center 模块**：新增概念关系的领域模型、Port 接口、Application Service、REST 端点；扩展 `IGraphRepository` 以支持概念关系的写入和查询；新增 PostgreSQL 持久化层（ORM Model + Repository + Alembic Migration）。
- **llm_platform 模块**：被 `knowledge_center` 通过 Port 调用，无需修改，但 KC 需新建对 `llm_platform` 的适配器。
- **Neo4j 图谱 Schema**：新增 Concept 间关系类型，需更新约束初始化逻辑。
- **PostgreSQL**：新增概念关系表（Single Source of Truth）。结构化字段：来源类型、置信度、确认状态、创建/更新时间、操作人；`ext_info`（JSONB）字段：存储 LLM 输入 prompt、原始输出、分析结果、推理依据、模型版本、手动创建时的备注说明等完整追溯上下文。Neo4j 可随时从此表全量重建。
- **REST API**：新增概念关系管理和查询端点（`/api/v1/knowledge-graph/concept-relations/...`）。
- **依赖关系**：`knowledge_center` 新增对 `llm_platform` 的 Port 依赖（通过适配器），符合支撑层互通规则。
