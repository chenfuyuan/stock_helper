# 知识中心 API 调用指南

> 本文档提供 Stock Helper 知识中心模块的完整 API 使用指南，包括图谱同步、查询和关系分析功能。

---

## 1. 概述

知识中心模块基于 Neo4j 图数据库构建，提供股票实体间的关联关系查询能力。通过 REST API 暴露以下核心功能：

- **图谱数据同步**：将 PostgreSQL 中的股票数据同步到 Neo4j 图谱
- **同维度股票查询**：查询同行业、同地域、同市场或同交易所的股票
- **个股关系网络**：获取指定股票的完整关联图谱

### API 基础信息

- **Base URL**: `http://localhost:8000/api/v1/knowledge-graph`
- **认证方式**: 暂无（开发环境）
- **数据格式**: JSON
- **字符编码**: UTF-8

---

## 2. 环境准备

### 2.1 启动服务

确保 Neo4j 和应用服务已启动：

```bash
# 启动所有服务
docker compose up -d

# 检查服务状态
docker compose ps
```

### 2.2 验证 Neo4j 连接

访问 [http://localhost:7474](http://localhost:7474) 确认 Neo4j Browser 可用，或使用 API 验证：

```bash
curl -X GET "http://localhost:8000/health" | jq
```

---

## 3. API 端点详解

### 3.1 图谱数据同步

**端点**: `POST /api/v1/knowledge-graph/sync`

**功能**: 将 PostgreSQL 中的股票数据同步到 Neo4j 图谱，支持全量和增量两种模式。

#### 3.1.1 全量同步

```bash
curl -X POST "http://localhost:8000/api/v1/knowledge-graph/sync" \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "full",
    "include_finance": false,
    "batch_size": 500,
    "skip": 0,
    "limit": 10000
  }'
```

**请求参数**:

| 参数 | 类型 | 必填 | 说明 | 默认值 |
|------|------|------|------|--------|
| `mode` | string | 是 | 同步模式，固定值 `"full"` | — |
| `include_finance` | boolean | 否 | 是否包含财务快照数据 | `false` |
| `batch_size` | integer | 否 | 批量处理大小 | `500` |
| `skip` | integer | 否 | 跳过前 N 条记录 | `0` |
| `limit` | integer | 否 | 查询数量上限 | `10000` |

**响应示例**:

```json
{
  "total": 4582,
  "success": 4582,
  "failed": 0,
  "duration_ms": 12543.2,
  "error_details": []
}
```

#### 3.1.2 增量同步

```bash
curl -X POST "http://localhost:8000/api/v1/knowledge-graph/sync" \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "incremental",
    "third_codes": ["000001.SZ", "000002.SZ"],
    "include_finance": true,
    "batch_size": 100
  }'
```

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `mode` | string | 是 | 同步模式，固定值 `"incremental"` |
| `third_codes` | array | 是 | 股票第三方代码列表 |
| `include_finance` | boolean | 否 | 是否包含财务快照数据 |
| `batch_size` | integer | 否 | 批量处理大小 |

---

### 3.2 同维度股票查询

**端点**: `GET /api/v1/knowledge-graph/stocks/{third_code}/neighbors`

**功能**: 根据指定维度查询与目标股票共享同一维度的其他股票。

#### 3.2.1 查询同行业股票

```bash
curl -X GET "http://localhost:8000/api/v1/knowledge-graph/stocks/000001.SZ/neighbors?dimension=industry&limit=10"
```

#### 3.2.2 查询同地域股票

```bash
curl -X GET "http://localhost:8000/api/v1/knowledge-graph/stocks/000001.SZ/neighbors?dimension=area&limit=15"
```

#### 3.2.3 查询同市场股票

```bash
curl -X GET "http://localhost:8000/api/v1/knowledge-graph/stocks/000001.SZ/neighbors?dimension=market&limit=20"
```

#### 3.2.4 查询同交易所股票

```bash
curl -X GET "http://localhost:8000/api/v1/knowledge-graph/stocks/000001.SZ/neighbors?dimension=exchange&limit=50"
```

**请求参数**:

| 参数 | 类型 | 必填 | 说明 | 可选值 |
|------|------|------|------|--------|
| `third_code` | string | 是 | 股票第三方代码（路径参数） | — |
| `dimension` | string | 是 | 查询维度 | `industry`, `area`, `market`, `exchange` |
| `limit` | integer | 否 | 返回数量上限 | 1-100，默认 20 |

**响应示例**:

```json
[
  {
    "third_code": "000002.SZ",
    "name": "万科A",
    "industry": "房地产",
    "area": "深圳",
    "market": "主板",
    "exchange": "深交所"
  },
  {
    "third_code": "000043.SZ",
    "name": "中航地产",
    "industry": "房地产",
    "area": "深圳",
    "market": "主板",
    "exchange": "深交所"
  }
]
```

---

### 3.3 个股关系网络查询

**端点**: `GET /api/v1/knowledge-graph/stocks/{third_code}/graph`

**功能**: 查询指定股票及其关联的维度节点和关系，构建完整的关联图谱。

#### 3.3.1 基础查询

```bash
curl -X GET "http://localhost:8000/api/v1/knowledge-graph/stocks/000001.SZ/graph?depth=1"
```

**请求参数**:

| 参数 | 类型 | 必填 | 说明 | 默认值 |
|------|------|------|------|--------|
| `third_code` | string | 是 | 股票第三方代码（路径参数） | — |
| `depth` | integer | 否 | 遍历深度 | `1`（MVP 阶段仅支持 1） |

**响应示例**:

```json
{
  "nodes": [
    {
      "label": "STOCK",
      "id": "000001.SZ",
      "properties": {
        "name": "平安银行",
        "industry": "银行",
        "area": "深圳",
        "market": "主板",
        "exchange": "深交所"
      }
    },
    {
      "label": "INDUSTRY",
      "id": "银行",
      "properties": {
        "name": "银行"
      }
    },
    {
      "label": "AREA",
      "id": "深圳",
      "properties": {
        "name": "深圳"
      }
    }
  ],
  "relationships": [
    {
      "source_id": "000001.SZ",
      "target_id": "银行",
      "relationship_type": "BELONGS_TO_INDUSTRY"
    },
    {
      "source_id": "000001.SZ",
      "target_id": "深圳",
      "relationship_type": "LOCATED_IN"
    }
  ]
}
```

---

## 4. 图谱数据模型

### 4.1 节点类型

| 节点标签 | 说明 | 主要属性 |
|----------|------|----------|
| `STOCK` | 股票节点 | `name`, `industry`, `area`, `market`, `exchange` |
| `INDUSTRY` | 行业节点 | `name` |
| `AREA` | 地域节点 | `name` |
| `MARKET` | 市场节点 | `name` |
| `EXCHANGE` | 交易所节点 | `name` |

### 4.2 关系类型

| 关系类型 | 源节点 | 目标节点 | 说明 |
|----------|--------|----------|------|
| `BELONGS_TO_INDUSTRY` | STOCK | INDUSTRY | 股票所属行业 |
| `LOCATED_IN` | STOCK | AREA | 股票所在地域 |
| `TRADES_ON` | STOCK | MARKET | 股票交易市场 |
| `LISTED_ON` | STOCK | EXCHANGE | 股票上市交易所 |

### 4.3 图谱结构示例

```
(STOCK:000001.SZ) -[:BELONGS_TO_INDUSTRY]-> (INDUSTRY:银行)
(STOCK:000001.SZ) -[:LOCATED_IN]-> (AREA:深圳)
(STOCK:000001.SZ) -[:TRADES_ON]-> (MARKET:主板)
(STOCK:000001.SZ) -[:LISTED_ON]-> (EXCHANGE:深交所)
```

---

## 5. 使用场景与示例

### 5.1 竞品分析

**场景**: 分析某股票的同行业竞争对手

```bash
# 1. 获取平安银行的所有同行业股票
curl -X GET "http://localhost:8000/api/v1/knowledge-graph/stocks/000001.SZ/neighbors?dimension=industry&limit=20"

# 2. 获取完整的行业关系图谱
curl -X GET "http://localhost:8000/api/v1/knowledge-graph/stocks/000001.SZ/graph"
```

### 5.2 地域板块分析

**场景**: 查找深圳地区的所有上市公司

```bash
# 查询同地域股票
curl -X GET "http://localhost:8000/api/v1/knowledge-graph/stocks/000001.SZ/neighbors?dimension=area&limit=50"
```

### 5.3 数据初始化

**场景**: 首次部署后初始化图谱数据

```bash
# 1. 全量同步基础股票信息
curl -X POST "http://localhost:8000/api/v1/knowledge-graph/sync" \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "full",
    "include_finance": false,
    "batch_size": 1000,
    "limit": 5000
  }'

# 2. 增量同步财务数据（可选）
curl -X POST "http://localhost:8000/api/v1/knowledge-graph/sync" \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "full",
    "include_finance": true,
    "batch_size": 500,
    "limit": 1000
  }'
```

---

## 6. 错误处理

### 6.1 常见错误码

| HTTP 状态码 | 错误类型 | 说明 | 解决方案 |
|-------------|----------|------|----------|
| `400` | 请求参数错误 | 参数缺失或格式错误 | 检查请求参数格式 |
| `404` | 资源不存在 | 指定的股票代码不存在 | 确认股票代码正确性 |
| `500` | 服务器内部错误 | Neo4j 连接失败或查询异常 | 检查 Neo4j 服务状态 |
| `503` | 服务不可用 | Neo4j 连接超时 | 重试或检查网络连接 |

### 6.2 错误响应示例

```json
{
  "detail": "Stock 节点不存在: 999999.SZ"
}
```

```json
{
  "detail": "增量同步模式下 third_codes 不能为空"
}
```

---

## 7. 性能优化建议

### 7.1 查询优化

- **限制返回数量**: 使用 `limit` 参数控制结果集大小
- **批量操作**: 增量同步时合理设置 `batch_size`（建议 500-1000）
- **缓存策略**: 对频繁查询的同维度股票结果进行缓存

### 7.2 同步优化

```bash
# 大数据量同步时的推荐参数
curl -X POST "http://localhost:8000/api/v1/knowledge-graph/sync" \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "full",
    "include_finance": false,
    "batch_size": 200,
    "skip": 0,
    "limit": 1000
  }'
```

---

## 8. 监控与调试

### 8.1 同步进度监控

同步响应中的 `duration_ms` 和 `error_details` 字段可用于监控同步性能和问题：

```json
{
  "total": 1000,
  "success": 998,
  "failed": 2,
  "duration_ms": 8567.3,
  "error_details": [
    "股票 000999.SZ 同步失败: 数据格式异常",
    "股票 001000.SZ 同步失败: 重复节点"
  ]
}
```

### 8.2 Neo4j 直接查询

通过 Neo4j Browser 直接查询图谱状态：

```cypher
-- 查看节点总数
MATCH (n) RETURN count(n) AS total_nodes

-- 查看关系总数
MATCH ()-[r]->() RETURN count(r) AS total_relationships

-- 查看特定股票的关系网络
MATCH (n:STOCK {id: "000001.SZ"})-[r]->(m)
RETURN n, r, m
```

---

## 9. 集成示例

### 9.1 Python 客户端示例

```python
import requests
from typing import List, Dict

class KnowledgeCenterClient:
    def __init__(self, base_url: str = "http://localhost:8000/api/v1/knowledge-graph"):
        self.base_url = base_url
    
    def sync_graph(self, mode: str = "full", **kwargs) -> Dict:
        """同步图谱数据"""
        payload = {"mode": mode, **kwargs}
        response = requests.post(f"{self.base_url}/sync", json=payload)
        response.raise_for_status()
        return response.json()
    
    def get_stock_neighbors(self, third_code: str, dimension: str, limit: int = 20) -> List[Dict]:
        """查询同维度股票"""
        params = {"dimension": dimension, "limit": limit}
        response = requests.get(f"{self.base_url}/stocks/{third_code}/neighbors", params=params)
        response.raise_for_status()
        return response.json()
    
    def get_stock_graph(self, third_code: str, depth: int = 1) -> Dict:
        """查询个股关系网络"""
        params = {"depth": depth}
        response = requests.get(f"{self.base_url}/stocks/{third_code}/graph", params=params)
        response.raise_for_status()
        return response.json()

# 使用示例
client = KnowledgeCenterClient()

# 查询同行业股票
neighbors = client.get_stock_neighbors("000001.SZ", "industry", limit=10)
print(f"同行业股票: {neighbors}")

# 获取关系图谱
graph = client.get_stock_graph("000001.SZ")
print(f"关系图谱: {graph}")
```

### 9.2 JavaScript 客户端示例

```javascript
class KnowledgeCenterAPI {
    constructor(baseUrl = 'http://localhost:8000/api/v1/knowledge-graph') {
        this.baseUrl = baseUrl;
    }

    async syncGraph(mode = 'full', options = {}) {
        const payload = { mode, ...options };
        const response = await fetch(`${this.baseUrl}/sync`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        return await response.json();
    }

    async getStockNeighbors(thirdCode, dimension, limit = 20) {
        const params = new URLSearchParams({ dimension, limit: limit.toString() });
        const response = await fetch(`${this.baseUrl}/stocks/${thirdCode}/neighbors?${params}`);
        return await response.json();
    }

    async getStockGraph(thirdCode, depth = 1) {
        const params = new URLSearchParams({ depth: depth.toString() });
        const response = await fetch(`${this.baseUrl}/stocks/${thirdCode}/graph?${params}`);
        return await response.json();
    }
}

// 使用示例
const api = new KnowledgeCenterAPI();

// 查询同行业股票
api.getStockNeighbors('000001.SZ', 'industry', 10)
    .then(neighbors => console.log('同行业股票:', neighbors))
    .catch(error => console.error('查询失败:', error));
```

---

## 10. 故障排查

### 10.1 常见问题

**Q1: API 返回 500 错误**
- 检查 Neo4j 容器是否正常运行：`docker compose ps neo4j`
- 查看 Neo4j 日志：`docker compose logs neo4j`
- 验证环境变量配置：确认 `.env` 中的 Neo4j 连接信息正确

**Q2: 查询结果为空**
- 确认图谱数据已同步：检查同步任务的 `total` 和 `success` 字段
- 在 Neo4j Browser 中执行 `MATCH (n) RETURN count(n)` 确认节点数
- 检查股票代码格式是否正确（如 "000001.SZ"）

**Q3: 同步任务失败**
- 检查 PostgreSQL 中是否有基础数据
- 查看 `data_engineering` 模块的日志
- 确认网络连接：应用容器能否访问 PostgreSQL 和 Neo4j

### 10.2 日志查看

```bash
# 查看应用日志
docker compose logs -f app

# 查看 Neo4j 日志
docker compose logs -f neo4j

# 实时监控 API 调用
docker compose logs app | grep "knowledge-graph"
```

---

## 11. 版本更新记录

| 版本 | 日期 | 更新内容 |
|------|------|----------|
| v1.0.0 | 2025-02-15 | 初始版本，支持图谱同步、同维度查询、关系网络查询 |

---

## 12. 相关文档

- [Neo4j 部署与运维指南](./neo4j-deployment.md)
- [知识中心模块设计文档](../openspec/changes/add-knowledge-center-mvp/)
- [Stock Helper 整体架构](../openspec/specs/vision-and-modules.md)

---

*本文档随代码更新同步维护，如有问题请提交 Issue 或 PR。*
