## Context

当前 `knowledge_center` 模块已具备完整的 Stock-Concept 图谱能力：Concept 节点通过 `BELONGS_TO_CONCEPT` 关系连接到 Stock，数据从 `data_engineering` 的 PostgreSQL 同步到 Neo4j。但 Concept 节点之间没有任何关系，是一组扁平的标签。

本次变更在 `knowledge_center` 模块内新增"概念关系"子域，建立 Concept 间的语义关系网络（上下游、竞争、组成、技术驱动等），并提供手动管理和 LLM 辅助推荐两条路径。

**核心约束**：
- PostgreSQL 为 Single Source of Truth，Neo4j 为派生查询视图，可随时全量重建。
- 所有关系记录必须带完整追溯信息（`ext_info` JSONB 字段）。
- 遵循现有 DDD 分层和 Port 通信规范。

## Goals / Non-Goals

**Goals:**

- 在 PostgreSQL 中建立概念关系的主数据表，支持完整的 CRUD 生命周期和审计追溯。
- 提供 REST API 手动创建、查询、更新、删除概念关系。
- 提供 LLM 辅助分析能力，自动推荐概念间关系，结果写入 PostgreSQL 待确认。
- 将已确认的关系同步到 Neo4j，构建 Concept 间的关系网络。
- 提供概念关系网络查询 API（上下游链路、关联概念）。
- Neo4j 可随时从 PostgreSQL 全量重建。

**Non-Goals:**

- 不做概念关系的自动确认（LLM 推荐始终需人工确认）。
- 不做概念热度、情绪等动态属性（属于 `market_insight` 模块范畴）。
- 不做 Concept 到 Stock 的传导分析（属于后续扩展，需 Research 模块参与）。
- 不修改现有的 Stock-Concept 同步流程（`BELONGS_TO_CONCEPT` 关系保持不变）。

## Decisions

### Decision 1：PostgreSQL 表设计 — 单表 + JSONB

**选择**：使用单张 `concept_relation` 表，结构化字段 + `ext_info`（JSONB）字段。

**方案对比**：

| 方案 | 优点 | 缺点 |
|------|------|------|
| A. 单表 + JSONB | 简单直接；ext_info 灵活适配不同来源；查询一次到位 | JSONB 内字段无 Schema 约束 |
| B. 多表（主表 + llm_detail 表 + manual_detail 表）| 每类来源有独立 Schema | 查询需 JOIN；表数量膨胀；新来源需建新表 |

**理由**：概念关系的核心结构（source、target、type、status）统一，来源差异体现在追溯上下文中。JSONB 的灵活性正好适合存储不同来源（手动 vs LLM）的异构追溯数据，且 PostgreSQL 对 JSONB 有 GIN 索引支持，查询性能可控。在应用层通过 Pydantic 对 `ext_info` 内容做校验，弥补 DB 层无 Schema 约束的问题。

**表结构**：

```
concept_relation
├── id              (BIGINT PK, auto-increment)
├── source_concept_code  (VARCHAR, FK 逻辑关联 concept.code)
├── target_concept_code  (VARCHAR, FK 逻辑关联 concept.code)
├── relation_type   (VARCHAR, 枚举: IS_UPSTREAM_OF / IS_DOWNSTREAM_OF / COMPETES_WITH / IS_PART_OF / ENABLER_FOR)
├── source_type     (VARCHAR, 枚举: MANUAL / LLM)
├── status          (VARCHAR, 枚举: PENDING / CONFIRMED / REJECTED)
├── confidence      (FLOAT, 0.0~1.0, 手动创建默认 1.0)
├── ext_info        (JSONB, 追溯上下文)
├── created_by      (VARCHAR, 操作人标识)
├── created_at      (TIMESTAMP WITH TZ)
├── updated_at      (TIMESTAMP WITH TZ)
├── UNIQUE (source_concept_code, target_concept_code, relation_type)
```

**`ext_info` 内容约定**：

- 手动来源：`{"note": "用户备注说明", "reason": "建立关系的理由"}`
- LLM 来源：`{"model": "模型名称", "model_version": "版本", "prompt": "完整输入prompt", "raw_output": "LLM原始输出", "parsed_result": {...}, "reasoning": "推理依据", "batch_id": "批次ID", "analyzed_at": "分析时间"}`

### Decision 2：Neo4j 关系建模 — 多关系类型 + 属性

**选择**：在 Neo4j 中使用独立的关系类型（`IS_UPSTREAM_OF`、`IS_DOWNSTREAM_OF` 等），每种关系类型对应 PostgreSQL 中的 `relation_type`。

**方案对比**：

| 方案 | 优点 | 缺点 |
|------|------|------|
| A. 多关系类型 | 图查询高效（可按类型筛选）；语义清晰；Cypher 模式匹配自然 | 新增关系类型需更新同步逻辑 |
| B. 单一 CONCEPT_RELATED 关系 + type 属性 | 同步逻辑简单；新增类型无需改代码 | 查询需额外过滤；丧失图数据库的语义优势 |

**理由**：图数据库的核心价值在于关系的语义化。使用独立关系类型，Cypher 查询可直接写 `(c1:Concept)-[:IS_UPSTREAM_OF]->(c2:Concept)`，模式匹配更自然高效。新增关系类型的频率预计很低（需要领域分析后才会扩展），维护成本可接受。

**关系属性**：每条关系携带 `source_type`、`confidence`、`pg_id`（关联 PostgreSQL 主键，用于反向追溯）。

### Decision 3：LLM 集成架构 — KC 定义 Port，Adapter 包装 LLMService

**选择**：在 `knowledge_center` 的 `domain/ports/` 中定义 `IConceptRelationAnalyzer` Port 接口，在 `infrastructure/adapters/` 中实现 `LLMConceptRelationAnalyzer`，通过注入 `llm_platform` 的 `LLMService` 完成调用。

**理由**：遵循现有的跨模块集成模式（与 Research 模块使用 `LLMAdapter` 调用 `LLMService` 的模式一致）。KC 的 Domain 层不感知 LLM 的存在，仅依赖抽象 Port。Prompt 工程和输出解析封装在 Adapter 内部，对上层透明。

**调用链路**：
```
ConceptRelationService (Application)
  → IConceptRelationAnalyzer (Domain Port)
    → LLMConceptRelationAnalyzer (Infrastructure Adapter)
      → LLMService (llm_platform Application Service)
        → LLMRouter → OpenAIProvider
```

### Decision 4：同步策略 — 全量重建 + 增量追加

**选择**：提供两种同步模式：

1. **全量重建**（rebuild）：删除 Neo4j 中所有 Concept 间关系 → 从 PostgreSQL 读取所有 `status=CONFIRMED` 的记录 → 批量写入 Neo4j。用于 Neo4j 数据修复或首次构建。
2. **增量追加**（incremental）：仅同步自上次同步后新增/变更的已确认关系。用于日常维护。

**理由**：全量重建保证 PostgreSQL → Neo4j 的一致性，是"可重建"承诺的兑现方式。增量追加降低日常运维开销。两种模式互补。

### Decision 5：模块归属 — 全部在 knowledge_center 内

**选择**：概念关系的所有代码（领域模型、持久化、LLM 集成、同步、查询）均归属 `knowledge_center` 模块。

**理由**：概念关系是知识图谱的核心组成部分，属于 KC 的 Bounded Context。PostgreSQL 持久化是 KC 内部的基础设施选择（与 DE 的 PostgreSQL 是不同的关注点）。LLM 集成通过 Port + Adapter 模式完成，不引入对 `llm_platform` 的直接依赖。

### Decision 6：API 路径设计

**选择**：在现有 `/api/v1/knowledge-graph/` 前缀下新增概念关系端点：

```
POST   /api/v1/knowledge-graph/concept-relations          # 手动创建
GET    /api/v1/knowledge-graph/concept-relations          # 列表查询（支持筛选）
GET    /api/v1/knowledge-graph/concept-relations/{id}     # 单条查询
PUT    /api/v1/knowledge-graph/concept-relations/{id}     # 更新（含确认/拒绝）
DELETE /api/v1/knowledge-graph/concept-relations/{id}     # 删除

POST   /api/v1/knowledge-graph/concept-relations/llm-suggest  # LLM 推荐
POST   /api/v1/knowledge-graph/concept-relations/sync         # 同步到 Neo4j

GET    /api/v1/knowledge-graph/concepts/{code}/relations      # 查询指定概念的关系网络
GET    /api/v1/knowledge-graph/concepts/{code}/chain          # 查询产业链路径
```

## Risks / Trade-offs

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| LLM 推荐质量不稳定 | 产生大量低质量关系建议 | 所有 LLM 推荐默认 PENDING 状态，必须人工确认；通过 confidence 阈值过滤低置信度建议；ext_info 中保留完整推理过程用于事后评估 |
| ext_info JSONB 缺乏 Schema 约束 | 数据结构不一致 | Application 层使用 Pydantic 子模型（`ManualExtInfo` / `LLMExtInfo`）校验 ext_info 内容；写入前强制校验 |
| Neo4j 与 PostgreSQL 数据不一致 | 查询结果与真实数据不符 | PostgreSQL 为 SSOT；Neo4j 仅展示已确认关系；提供全量重建命令随时修复；关系上携带 `pg_id` 可反向校验 |
| Concept 关系类型未来可能扩展 | 需同步更新枚举、Neo4j 关系类型、同步逻辑 | 关系类型定义为领域枚举，集中管理；同步逻辑基于枚举遍历，新增类型只需扩展枚举 |
| knowledge_center 首次引入 PostgreSQL 持久化 | 增加模块复杂度 | KC 原本仅依赖 Neo4j；新增 PG 持久化遵循现有模式（ORM Model + Repository + Alembic Migration），与 DE 模块模式一致 |
