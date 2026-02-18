## Why

当前的概念关系功能基于错误的假设——将不同维度的"概念"（如"参股银行"、"参股保险"等投资属性概念与"低空经济"等产业概念）混为一谈，建立伪产业链关系。这导致：
1. 无意义的关联关系误导用户和LLM分析
2. 系统复杂度增加但价值有限
3. 数据模型语义混乱，难以维护

## What Changes

- **BREAKING**: 删除完整的概念关系功能模块
- **BREAKING**: 移除所有概念关系相关的API端点
- **BREAKING**: 删除Neo4j图数据库中的概念关系存储
- **BREAKING**: 移除LLM概念关系推荐功能
- 保留基础的概念板块信息（Concept实体）和股票-概念映射关系
- 清理相关的数据库表、模型、服务和路由

## Capabilities

### Modified Capabilities
- `knowledge-center`: 移除概念关系管理能力，保留基础概念查询功能

## Impact

- **代码删除**: src/modules/knowledge_center/ 下的概念关系相关文件
- **API变更**: 删除 `/api/v1/knowledge-graph/concept-relations/*` 端点
- **数据库**: 删除 concept_relation 表，清理 Neo4j 中的概念关系数据
- **依赖**: 移除对 Neo4j 图数据库的依赖（如果仅用于概念关系）
- **文档**: 更新API文档和用户指南
