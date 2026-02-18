# 概念关系 API 文档 (已废弃)

**⚠️ 重要提醒**: 概念关系功能已被移除，原因是该功能基于错误假设，将不同维度的"概念"混为一谈建立伪产业链关系。

## 移除的功能

以下API端点已不再可用：
- `POST /api/v1/knowledge-graph/concept-relations` - 创建概念关系
- `GET /api/v1/knowledge-graph/concept-relations` - 查询概念关系列表  
- `GET /api/v1/knowledge-graph/concept-relations/{id}` - 查询单条概念关系
- `PUT /api/v1/knowledge-graph/concept-relations/{id}` - 更新概念关系
- `DELETE /api/v1/knowledge-graph/concept-relations/{id}` - 删除概念关系
- `POST /api/v1/knowledge-graph/concept-relations/llm-suggest` - LLM推荐概念关系
- `POST /api/v1/knowledge-graph/concept-relations/sync` - 同步概念关系
- `GET /api/v1/knowledge-graph/concepts/{code}/relations` - 查询概念关系网络
- `GET /api/v1/knowledge-graph/concepts/{code}/chain` - 查询产业链路径

## 保留的功能

以下功能仍然可用：
- 基础概念板块信息查询
- 股票-概念映射关系查询  
- 股票图谱查询和同步

请使用股票图谱相关API进行数据分析。
