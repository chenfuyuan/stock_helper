# 概念关系 API 文档

## 基础查询

### 查看所有概念关系
```bash
curl "http://localhost:8000/api/v1/knowledge-graph/concept-relations?limit=10"
```

### 查看特定概念的关系
```bash
curl "http://localhost:8000/api/v1/knowledge-graph/concepts/BK0729/relations"
```

### 查询产业链路径
```bash
curl "http://localhost:8000/api/v1/knowledge-graph/concepts/BK0729/chain?direction=outgoing&max_depth=2"
```

## LLM 智能分析

### LLM 推荐概念关系
```bash
curl -X POST http://localhost:8000/api/v1/knowledge-graph/concept-relations/llm-suggest \
  -H "Content-Type: application/json" \
  -d '{
    "concept_codes_with_names": [
      ["BK0729", "银行"],
      ["BK0480", "证券"],
      ["BK0625", "保险"]
    ],
    "min_confidence": 0.6
  }'
```

## 手动管理

### 创建手动关系
```bash
curl -X POST http://localhost:8000/api/v1/knowledge-graph/concept-relations \
  -H "Content-Type: application/json" \
  -d '{
    "source_concept_code": "BK0729",
    "target_concept_code": "BK0480",
    "relation_type": "IS_UPSTREAM_OF",
    "note": "银行是证券的上游资金来源",
    "reason": "银行提供资金支持证券业务发展"
  }'
```

### 更新关系状态
```bash
curl -X PUT http://localhost:8000/api/v1/knowledge-graph/concept-relations/{id} \
  -H "Content-Type: application/json" \
  -d '{"status": "CONFIRMED"}'
```

### 删除关系
```bash
curl -X DELETE http://localhost:8000/api/v1/knowledge-graph/concept-relations/{id}
```

## 数据同步

### 同步到 Neo4j
```bash
curl -X POST http://localhost:8000/api/v1/knowledge-graph/concept-relations/sync \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "incremental",
    "batch_size": 100
  }'
```

### 重建同步
```bash
curl -X POST http://localhost:8000/api/v1/knowledge-graph/concept-relations/sync \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "rebuild",
    "batch_size": 100
  }'
```

## 高级查询

### 按状态筛选
```bash
curl "http://localhost:8000/api/v1/knowledge-graph/concept-relations?status=CONFIRMED"
```

### 按关系类型筛选
```bash
curl "http://localhost:8000/api/v1/knowledge-graph/concept-relations?relation_type=COMPETES_WITH"
```

### 按置信度筛选
```bash
curl "http://localhost:8000/api/v1/knowledge-graph/concept-relations?min_confidence=0.7"
```

## 关系类型说明

- `IS_UPSTREAM_OF` - 上游关系
- `IS_DOWNSTREAM_OF` - 下游关系  
- `COMPETES_WITH` - 竞争关系
- `IS_PART_OF` - 组成关系
- `ENABLER_FOR` - 赋能关系
