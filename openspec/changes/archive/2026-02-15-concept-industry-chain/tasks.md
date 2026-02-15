## 1. Domain 层 — 领域模型与枚举

- [x] 1.1 在 `knowledge_center/domain/model/enums.py` 中新增 `ConceptRelationType`、`RelationSourceType`、`RelationStatus` 三个枚举
- [x] 1.2 在 `knowledge_center/domain/model/concept_relation.py` 中定义 `ConceptRelation` 领域实体（Pydantic BaseModel，含所有字段和默认值逻辑）

## 2. Domain 层 — DTOs

- [x] 2.1 在 `knowledge_center/domain/dtos/concept_relation_sync_dtos.py` 中定义 `ConceptRelationSyncDTO`（用于 PG → Neo4j 同步）
- [x] 2.2 在 `knowledge_center/domain/dtos/concept_relation_query_dtos.py` 中定义 `ConceptRelationQueryDTO` 和 `ConceptChainNodeDTO`（用于图查询返回）
- [x] 2.3 在 `knowledge_center/domain/dtos/concept_relation_analyzer_dtos.py` 中定义 `ConceptForAnalysis` 和 `SuggestedRelation`（用于 LLM 分析输入输出）
- [x] 2.4 在 `knowledge_center/domain/dtos/` 或 `application/dtos/` 中定义 `ManualExtInfo` 和 `LLMExtInfo` Pydantic 子模型（ext_info 校验）

## 3. Domain 层 — Ports

- [x] 3.1 在 `knowledge_center/domain/ports/concept_relation_repository.py` 中定义 `IConceptRelationRepository` ABC 接口（create / get_by_id / list_relations / update / delete / batch_create / get_all_confirmed / count）
- [x] 3.2 在 `knowledge_center/domain/ports/concept_relation_analyzer.py` 中定义 `IConceptRelationAnalyzer` ABC 接口（analyze_relations）
- [x] 3.3 扩展 `knowledge_center/domain/ports/graph_repository.py` 的 `IGraphRepository` 接口，新增 `merge_concept_relations`、`delete_all_concept_inter_relationships`、`find_concept_relations`、`find_concept_chain` 方法

## 4. Infrastructure 层 — PostgreSQL 持久化

- [x] 4.1 在 `knowledge_center/infrastructure/persistence/` 下创建 `concept_relation_model.py`（SQLAlchemy ORM Model，映射 `concept_relation` 表）
- [x] 4.2 创建 Alembic Migration：创建 `concept_relation` 表（含所有字段、唯一约束、CHECK 约束）
- [x] 4.3 在 `knowledge_center/infrastructure/persistence/` 下实现 `PgConceptRelationRepository`（实现 `IConceptRelationRepository` 接口）

## 5. Infrastructure 层 — Neo4j 图谱扩展

- [x] 5.1 扩展 `Neo4jGraphRepository`，实现 `merge_concept_relations` 方法（Cypher UNWIND + MATCH Concept + MERGE 关系，携带 source_type / confidence / pg_id 属性）
- [x] 5.2 扩展 `Neo4jGraphRepository`，实现 `delete_all_concept_inter_relationships` 方法（仅删 Concept 间关系，保留 Stock-Concept 关系）
- [x] 5.3 扩展 `Neo4jGraphRepository`，实现 `find_concept_relations` 方法（查询指定概念的双向直接关系）
- [x] 5.4 扩展 `Neo4jGraphRepository`，实现 `find_concept_chain` 方法（变长路径遍历，支持 direction 和 max_depth）

## 6. Infrastructure 层 — LLM 适配器

- [x] 6.1 在 `knowledge_center/infrastructure/adapters/llm_concept_relation_analyzer.py` 中实现 `LLMConceptRelationAnalyzer`（实现 `IConceptRelationAnalyzer`，注入 `LLMService`）
- [x] 6.2 实现 Prompt 工程：构建 system_message（产业链分析专家角色）和 user prompt（概念列表 + JSON 输出格式约束 + 关系类型枚举）
- [x] 6.3 实现 LLM 输出解析：解析 JSON 响应为 `SuggestedRelation` 列表，格式异常时降级返回空列表 + WARNING 日志

## 7. Application 层 — 服务与命令

- [x] 7.1 在 `knowledge_center/application/services/` 下创建 `ConceptRelationService`（聚合 CRUD 操作，注入 `IConceptRelationRepository`，含 ext_info 校验逻辑）
- [x] 7.2 在 `knowledge_center/application/commands/suggest_concept_relations_command.py` 中实现 `SuggestConceptRelationsCmd`（编排 LLM 推荐流程：查询概念 → 调用 Analyzer → 构建 ext_info → 批量写入 PG → 过滤重复）
- [x] 7.3 在 `knowledge_center/application/commands/sync_concept_relations_command.py` 中实现 `SyncConceptRelationsCmd`（编排 PG → Neo4j 同步，支持 rebuild / incremental 模式）

## 8. Application 层 — API DTOs

- [x] 8.1 在 `knowledge_center/application/dtos/` 下创建概念关系相关的 Request / Response DTO（CreateConceptRelationRequest、UpdateConceptRelationRequest、LLMSuggestRequest、SyncConceptRelationsRequest 及对应 Response）

## 9. Presentation 层 — REST 端点

- [x] 9.1 创建 `knowledge_center/presentation/rest/concept_relation_router.py`，实现 CRUD 端点（POST / GET / GET{id} / PUT / DELETE /api/v1/knowledge-graph/concept-relations）
- [x] 9.2 实现 LLM 推荐端点（POST /api/v1/knowledge-graph/concept-relations/llm-suggest）
- [x] 9.3 实现同步端点（POST /api/v1/knowledge-graph/concept-relations/sync）
- [x] 9.4 实现概念关系查询端点（GET /api/v1/knowledge-graph/concepts/{code}/relations）
- [x] 9.5 实现产业链路径查询端点（GET /api/v1/knowledge-graph/concepts/{code}/chain）
- [x] 9.6 在 FastAPI app 中注册新的 router

## 10. DI Container 与布线

- [x] 10.1 更新 `KnowledgeCenterContainer`，注册 `PgConceptRelationRepository`、`LLMConceptRelationAnalyzer`、`ConceptRelationService`、`SuggestConceptRelationsCmd`、`SyncConceptRelationsCmd`
- [x] 10.2 在 Container 中配置 `LLMService` 注入链路（从 `LLMPlatformContainer` 获取 `LLMService` → 注入 `LLMConceptRelationAnalyzer`）

## 11. 测试

- [x] 11.1 单元测试：`ConceptRelation` 实体默认值逻辑、枚举值完整性
- [x] 11.2 单元测试：`ManualExtInfo` / `LLMExtInfo` Pydantic 校验（通过与拒绝场景）
- [x] 11.3 单元测试：`LLMConceptRelationAnalyzer` 的 prompt 构建和输出解析（mock LLMService）
- [x] 11.4 单元测试：`SuggestConceptRelationsCmd` 流程编排（mock Analyzer + Repository，验证 ext_info 内容、重复跳过逻辑）
- [x] 11.5 单元测试：`SyncConceptRelationsCmd` 流程编排（mock Repository + GraphRepository，验证 rebuild / incremental 模式）
- [x] 11.6 集成测试：`PgConceptRelationRepository` CRUD（连接测试数据库，验证唯一约束、ext_info JSONB 存取）
- [x] 11.7 集成测试：`Neo4jGraphRepository` 概念关系相关方法（连接测试 Neo4j，验证 MERGE / 删除 / 查询 / 链路遍历）
- [x] 11.8 集成测试：REST 端点 E2E（通过 TestClient 验证各端点的正常与异常场景）
