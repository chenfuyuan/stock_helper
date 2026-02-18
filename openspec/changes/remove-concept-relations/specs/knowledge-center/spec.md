## REMOVED Requirements

### Requirement: ConceptRelation 领域实体定义
**Reason**: 概念关系功能基于错误假设，将不同维度的概念混为一谈建立伪产业链关系
**Migration**: 删除所有概念关系相关代码和数据，保留基础概念板块功能

### Requirement: ConceptRelation 数据库模型
**Reason**: 概念关系功能将被完全移除
**Migration**: 通过Alembic迁移删除concept_relation表

### Requirement: REST API — 创建概念关系
**Reason**: 概念关系创建功能将被移除
**Migration**: 删除 `/api/v1/knowledge-graph/concept-relations` POST端点

### Requirement: REST API — 列表查询概念关系
**Reason**: 概念关系查询功能将被移除
**Migration**: 删除 `/api/v1/knowledge-graph/concept-relations` GET端点

### Requirement: REST API — 查询单条概念关系
**Reason**: 概念关系查询功能将被移除
**Migration**: 删除 `/api/v1/knowledge-graph/concept-relations/{id}` GET端点

### Requirement: REST API — 更新概念关系
**Reason**: 概念关系更新功能将被移除
**Migration**: 删除 `/api/v1/knowledge-graph/concept-relations/{id}` PUT端点

### Requirement: REST API — 删除概念关系
**Reason**: 概念关系删除功能将被移除
**Migration**: 删除 `/api/v1/knowledge-graph/concept-relations/{id}` DELETE端点

### Requirement: SyncConceptRelationsCmd 同步命令
**Reason**: 概念关系同步功能将被移除
**Migration**: 删除SyncConceptRelationsCommand和相关服务

### Requirement: REST API — 同步概念关系
**Reason**: 概念关系同步API将被移除
**Migration**: 删除 `/api/v1/knowledge-graph/concept-relations/sync` POST端点

### Requirement: 查询指定概念的直接关系
**Reason**: 概念关系查询功能将被移除
**Migration**: 删除GraphRepository中的概念关系查询方法

### Requirement: 查询产业链路径
**Reason**: 产业链路径查询基于伪概念关系，将被移除
**Migration**: 删除find_concept_chain相关方法

### Requirement: IConceptRelationAnalyzer Port 定义
**Reason**: LLM概念关系推荐功能将被移除
**Migration**: 删除IConceptRelationAnalyzer接口和实现

### Requirement: SuggestConceptRelationsCmd 推荐命令
**Reason**: LLM概念关系推荐功能将被移除
**Migration**: 删除SuggestConceptRelationsCommand和相关服务

### Requirement: REST API — LLM 推荐概念关系
**Reason**: LLM概念关系推荐API将被移除
**Migration**: 删除 `/api/v1/knowledge-graph/concept-relations/llm-suggest` POST端点

## REMOVED Capabilities

以下capabilities将被完全移除：
- concept-relation-management
- concept-relation-graph-sync  
- concept-relation-graph-query
- concept-relation-llm-suggest

**Reason**: 这些capabilities都基于错误的概念关系假设，提供无价值的伪产业链分析功能

**Migration**: 完全删除相关代码、API端点、数据库表和文档
