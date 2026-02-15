# 知识中心 API 调用用法

> 本文档提供 Stock Helper 知识中心模块的 curl 调用示例，仅包含可直接执行的 API 请求。

---

## 1. 图谱数据同步

### 1.1 全量同步股票数据

```bash
curl -X POST "http://localhost:8000/api/v1/knowledge-graph/sync" \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "full",
    "target": "stock",
    "include_finance": false,
    "batch_size": 500,
    "skip": 0,
    "limit": 10000
  }'
```

### 1.2 全量同步概念数据

```bash
curl -X POST "http://localhost:8000/api/v1/knowledge-graph/sync" \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "full",
    "target": "concept",
    "batch_size": 500
  }'
```

### 1.3 全量同步所有数据（股票+概念）

```bash
curl -X POST "http://localhost:8000/api/v1/knowledge-graph/sync" \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "full",
    "target": "all",
    "include_finance": false,
    "batch_size": 500
  }'
```

### 1.4 增量同步指定股票

```bash
curl -X POST "http://localhost:8000/api/v1/knowledge-graph/sync" \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "incremental",
    "third_codes": ["000001.SZ", "000002.SZ", "600000.SH"],
    "include_finance": true,
    "batch_size": 100
  }'
```

---

## 2. 同维度股票查询

### 2.1 查询同行业股票

```bash
curl -X GET "http://localhost:8000/api/v1/knowledge-graph/stocks/000001.SZ/neighbors?dimension=industry&limit=10"
```

### 2.2 查询同地域股票

```bash
curl -X GET "http://localhost:8000/api/v1/knowledge-graph/stocks/000001.SZ/neighbors?dimension=area&limit=15"
```

### 2.3 查询同市场股票

```bash
curl -X GET "http://localhost:8000/api/v1/knowledge-graph/stocks/000001.SZ/neighbors?dimension=market&limit=20"
```

### 2.4 查询同交易所股票

```bash
curl -X GET "http://localhost:8000/api/v1/knowledge-graph/stocks/000001.SZ/neighbors?dimension=exchange&limit=50"
```

### 2.5 查询同概念股票

```bash
# 查询"船舶制造"概念的所有股票
curl -X GET "http://localhost:8000/api/v1/knowledge-graph/stocks/300008.SZ/neighbors?dimension=concept&dimension_name=船舶制造&limit=20"

# 查询"军工"概念的所有股票
curl -X GET "http://localhost:8000/api/v1/knowledge-graph/stocks/300008.SZ/neighbors?dimension=concept&dimension_name=军工&limit=20"

# 查询"人工智能"概念的所有股票
curl -X GET "http://localhost:8000/api/v1/knowledge-graph/stocks/002230.SZ/neighbors?dimension=concept&dimension_name=人工智能&limit=20"
```

---

## 3. 个股关系网络查询

### 3.1 基础关系网络

```bash
curl -X GET "http://localhost:8000/api/v1/knowledge-graph/stocks/000001.SZ/graph?depth=1"
```

### 3.2 查询不同股票的关系网络

```bash
# 平安银行
curl -X GET "http://localhost:8000/api/v1/knowledge-graph/stocks/000001.SZ/graph"

# 万科A
curl -X GET "http://localhost:8000/api/v1/knowledge-graph/stocks/000002.SZ/graph"

# 天海防务（包含概念关系）
curl -X GET "http://localhost:8000/api/v1/knowledge-graph/stocks/300008.SZ/graph"

# 中国平安
curl -X GET "http://localhost:8000/api/v1/knowledge-graph/stocks/601318.SH/graph"
```

---

## 4. 常用查询组合

### 4.1 完整的数据初始化流程

```bash
# 1. 同步股票基础数据
curl -X POST "http://localhost:8000/api/v1/knowledge-graph/sync" \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "full",
    "target": "stock",
    "include_finance": false,
    "batch_size": 1000
  }'

# 2. 同步概念数据
curl -X POST "http://localhost:8000/api/v1/knowledge-graph/sync" \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "full",
    "target": "concept",
    "batch_size": 500
  }'

# 3. 验证同步结果
curl -X GET "http://localhost:8000/api/v1/knowledge-graph/stocks/000001.SZ/graph"
```

### 4.2 概念板块分析

```bash
# 1. 查询某股票的所有概念
curl -X GET "http://localhost:8000/api/v1/knowledge-graph/stocks/300008.SZ/graph"

# 2. 查询"军工"概念的所有股票
curl -X GET "http://localhost:8000/api/v1/knowledge-graph/stocks/300008.SZ/neighbors?dimension=concept&dimension_name=军工&limit=50"

# 3. 查询"船舶制造"概念的所有股票
curl -X GET "http://localhost:8000/api/v1/knowledge-graph/stocks/300008.SZ/neighbors?dimension=concept&dimension_name=船舶制造&limit=50"
```

### 4.3 竞品分析

```bash
# 1. 查询同行业竞争对手
curl -X GET "http://localhost:8000/api/v1/knowledge-graph/stocks/000001.SZ/neighbors?dimension=industry&limit=20"

# 2. 查询同地域公司
curl -X GET "http://localhost:8000/api/v1/knowledge-graph/stocks/000001.SZ/neighbors?dimension=area&limit=30"

# 3. 查询同概念股票
curl -X GET "http://localhost:8000/api/v1/knowledge-graph/stocks/000001.SZ/neighbors?dimension=concept&dimension_name=银行&limit=20"
```

---

## 5. 参数说明

### 5.1 同步 API 参数

| 参数 | 类型 | 说明 | 可选值 |
|------|------|------|--------|
| `mode` | string | 同步模式 | `"full"`, `"incremental"` |
| `target` | string | 同步目标 | `"stock"`, `"concept"`, `"all"` |
| `include_finance` | boolean | 是否包含财务数据 | `true`, `false` |
| `batch_size` | integer | 批量处理大小 | 100-2000 |
| `third_codes` | array | 股票代码列表（增量模式必需） | `["000001.SZ"]` |
| `skip` | integer | 跳过记录数 | 0+ |
| `limit` | integer | 处理记录上限 | 1-10000 |

### 5.2 查询 API 参数

| 参数 | 类型 | 说明 | 可选值 |
|------|------|------|--------|
| `dimension` | string | 查询维度 | `"industry"`, `"area"`, `"market"`, `"exchange"`, `"concept"` |
| `dimension_name` | string | 维度名称（concept 维度必需） | 概念名称 |
| `limit` | integer | 返回数量上限 | 1-100 |
| `depth` | integer | 遍历深度 | 1（当前仅支持 1） |

---

## 6. 响应示例

### 6.1 同步响应

```json
{
  "total": 466,
  "success": 466,
  "failed": 0,
  "duration_ms": 1807.94,
  "error_details": []
}
```

### 6.2 邻居查询响应

```json
[
  {
    "third_code": "300065.SZ",
    "name": "海兰信",
    "industry": null,
    "area": null,
    "market": null,
    "exchange": null
  },
  {
    "third_code": "600482.SH",
    "name": "中国动力",
    "industry": null,
    "area": null,
    "market": null,
    "exchange": null
  }
]
```

### 6.3 关系网络响应

```json
{
  "nodes": [
    {
      "label": "STOCK",
      "id": "300008.SZ",
      "properties": {
        "name": "天海防务",
        "third_code": "300008.SZ"
      }
    },
    {
      "label": "CONCEPT",
      "id": "船舶制造",
      "properties": {
        "code": "BK0729",
        "name": "船舶制造"
      }
    }
  ],
  "relationships": [
    {
      "source_id": "300008.SZ",
      "target_id": "船舶制造",
      "relationship_type": "BELONGS_TO_CONCEPT"
    }
  ]
}
```

---

*本文档仅包含 API 调用示例，详细说明请参考 [知识中心 API 完整指南](./knowledge-center-api-guide.md)。*
