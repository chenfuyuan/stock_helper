# Knowledge Graph API Curl 测试文档

本文档提供知识图谱 REST API 的 curl 测试示例，涵盖所有主要功能的使用方法。

## 基础配置

```bash
# API 基础 URL（根据实际部署调整）
BASE_URL="http://localhost:8000/api/v1"

# 通用请求头
HEADERS="Content-Type: application/json"
```

---

## 1. 查询同维度股票

### 1.1 查询同行业股票

```bash
curl -X GET "$BASE_URL/knowledge-graph/stocks/000001.SZ/neighbors?dimension=industry&limit=10" \
  -H "$HEADERS"
```

**响应示例**:
```json
[
  {
    "third_code": "601398.SH",
    "name": "工商银行",
    "industry": "银行",
    "area": null,
    "market": null,
    "exchange": null
  },
  {
    "third_code": "601939.SH",
    "name": "建设银行",
    "industry": "银行",
    "area": null,
    "market": null,
    "exchange": null
  }
]
```

### 1.2 查询同地域股票

```bash
curl -X GET "$BASE_URL/knowledge-graph/stocks/000001.SZ/neighbors?dimension=area&limit=15" \
  -H "$HEADERS"
```

### 1.3 查询同市场股票

```bash
curl -X GET "$BASE_URL/knowledge-graph/stocks/000001.SZ/neighbors?dimension=market&limit=20" \
  -H "$HEADERS"
```

### 1.4 查询同交易所股票

```bash
curl -X GET "$BASE_URL/knowledge-graph/stocks/000001.SZ/neighbors?dimension=exchange&limit=10" \
  -H "$HEADERS"
```

### 1.5 查询同概念股票

```bash
curl -X GET "$BASE_URL/knowledge-graph/stocks/000001.SZ/neighbors?dimension=concept&dimension_name=低空经济&limit=10" \
  -H "$HEADERS"
```

**注意**: `dimension_name` 参数在查询概念维度时必须提供。

### 1.6 错误场景测试

#### 缺少必需的 dimension_name 参数
```bash
curl -X GET "$BASE_URL/knowledge-graph/stocks/000001.SZ/neighbors?dimension=concept" \
  -H "$HEADERS"
# 预期响应: HTTP 422 - "查询概念维度邻居时必须提供 dimension_name 参数"
```

#### 无效的维度类型
```bash
curl -X GET "$BASE_URL/knowledge-graph/stocks/000001.SZ/neighbors?dimension=invalid" \
  -H "$HEADERS"
# 预期响应: HTTP 422 - 参数验证错误
```

#### 不存在的股票代码
```bash
curl -X GET "$BASE_URL/knowledge-graph/stocks/999999.XX/neighbors?dimension=industry" \
  -H "$HEADERS"
# 预期响应: HTTP 200 - 空数组 []
```

---

## 2. 查询个股关系网络

### 2.1 基本查询

```bash
curl -X GET "$BASE_URL/knowledge-graph/stocks/000001.SZ/graph" \
  -H "$HEADERS"
```

**响应示例**:
```json
{
  "nodes": [
    {
      "label": "STOCK",
      "id": "000001.SZ",
      "properties": {
        "third_code": "000001.SZ",
        "symbol": "平安银行",
        "name": "平安银行",
        "fullname": "平安银行股份有限公司",
        "list_date": "19910403",
        "list_status": "L",
        "curr_type": "CNY"
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
      "label": "CONCEPT",
      "id": "BK0493",
      "properties": {
        "code": "BK0493",
        "name": "低空经济"
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
      "target_id": "BK0493",
      "relationship_type": "BELONGS_TO_CONCEPT"
    }
  ]
}
```

### 2.2 指定深度查询

```bash
# MVP 阶段仅支持 depth=1
curl -X GET "$BASE_URL/knowledge-graph/stocks/000001.SZ/graph?depth=1" \
  -H "$HEADERS"
```

### 2.3 错误场景测试

#### 不存在的股票代码
```bash
curl -X GET "$BASE_URL/knowledge-graph/stocks/999999.XX/graph" \
  -H "$HEADERS"
# 预期响应: HTTP 200 - null
```

#### 无效的深度参数
```bash
curl -X GET "$BASE_URL/knowledge-graph/stocks/000001.SZ/graph?depth=2" \
  -H "$HEADERS"
# 预期响应: HTTP 422 - 参数验证错误
```

---

## 3. 同步图谱数据

### 3.1 股票数据全量同步

```bash
curl -X POST "$BASE_URL/knowledge-graph/sync" \
  -H "$HEADERS" \
  -d '{
    "mode": "full",
    "target": "stock",
    "include_finance": false,
    "batch_size": 500,
    "skip": 0,
    "limit": 10000
  }'
```

### 3.2 股票数据增量同步

```bash
curl -X POST "$BASE_URL/knowledge-graph/sync" \
  -H "$HEADERS" \
  -d '{
    "mode": "incremental",
    "target": "stock",
    "third_codes": ["000001.SZ", "601398.SH"],
    "include_finance": false,
    "batch_size": 500,
    "window_days": 3,
    "limit": 10000
  }'
```

### 3.3 概念数据全量同步

```bash
curl -X POST "$BASE_URL/knowledge-graph/sync" \
  -H "$HEADERS" \
  -d '{
    "mode": "full",
    "target": "concept",
    "batch_size": 500
  }'
```

**注意**: 概念同步仅支持全量模式，会忽略 `mode` 和 `third_codes` 参数。

### 3.4 全部数据同步（股票 + 概念）

```bash
curl -X POST "$BASE_URL/knowledge-graph/sync" \
  -H "$HEADERS" \
  -d '{
    "mode": "full",
    "target": "all",
    "include_finance": true,
    "batch_size": 500,
    "skip": 0,
    "limit": 10000
  }'
```

### 3.5 同步结果示例

```json
{
  "total": 5200,
  "success": 5185,
  "failed": 15,
  "duration_ms": 15432.56,
  "error_details": [
    "third_code=000002.SZ 同步失败: 数据格式异常",
    "third_code=000003.SZ 同步失败: Neo4j 连接超时"
  ]
}
```

### 3.6 错误场景测试

#### 无效的同步模式
```bash
curl -X POST "$BASE_URL/knowledge-graph/sync" \
  -H "$HEADERS" \
  -d '{
    "mode": "invalid",
    "target": "stock"
  }'
# 预期响应: HTTP 400 - "无效的同步模式: invalid"
```

#### 缺少必需参数
```bash
curl -X POST "$BASE_URL/knowledge-graph/sync" \
  -H "$HEADERS" \
  -d '{}'
# 预期响应: HTTP 422 - 参数验证错误
```

---

## 4. 清空知识图谱

### 4.1 清空所有图谱数据

```bash
curl -X DELETE "$BASE_URL/knowledge-graph/clear" \
  -H "$HEADERS"
```

**⚠️ 警告**: 此操作不可逆，会删除所有节点和关系！

### 4.2 清空结果示例

```json
{
  "deleted_nodes": 5200,
  "deleted_relationships": 15800,
  "message": "成功清空图谱，删除了 5200 个节点和 15800 条关系"
}
```

---

## 5. 完整测试脚本

### 5.1 基础功能测试

```bash
#!/bin/bash

BASE_URL="http://localhost:8000/api/v1"
HEADERS="Content-Type: application/json"

echo "=== Knowledge Graph API 测试 ==="

# 1. 查询同行业股票
echo "1. 查询同行业股票..."
curl -X GET "$BASE_URL/knowledge-graph/stocks/000001.SZ/neighbors?dimension=industry&limit=5" \
  -H "$HEADERS" | jq .

# 2. 查询同概念股票
echo "2. 查询同概念股票..."
curl -X GET "$BASE_URL/knowledge-graph/stocks/000001.SZ/neighbors?dimension=concept&dimension_name=低空经济&limit=5" \
  -H "$HEADERS" | jq .

# 3. 查询个股关系网络
echo "3. 查询个股关系网络..."
curl -X GET "$BASE_URL/knowledge-graph/stocks/000001.SZ/graph" \
  -H "$HEADERS" | jq .

# 4. 触发概念同步
echo "4. 触发概念同步..."
curl -X POST "$BASE_URL/knowledge-graph/sync" \
  -H "$HEADERS" \
  -d '{
    "mode": "full",
    "target": "concept",
    "batch_size": 100
  }' | jq .

echo "=== 测试完成 ==="
```

### 5.2 错误场景测试

```bash
#!/bin/bash

BASE_URL="http://localhost:8000/api/v1"
HEADERS="Content-Type: application/json"

echo "=== 错误场景测试 ==="

# 1. 概念查询缺少 dimension_name
echo "1. 概念查询缺少 dimension_name..."
curl -X GET "$BASE_URL/knowledge-graph/stocks/000001.SZ/neighbors?dimension=concept" \
  -H "$HEADERS" -w "\nHTTP Status: %{http_code}\n"

# 2. 无效维度类型
echo "2. 无效维度类型..."
curl -X GET "$BASE_URL/knowledge-graph/stocks/000001.SZ/neighbors?dimension=invalid" \
  -H "$HEADERS" -w "\nHTTP Status: %{http_code}\n"

# 3. 不存在的股票
echo "3. 不存在的股票..."
curl -X GET "$BASE_URL/knowledge-graph/stocks/999999.XX/neighbors?dimension=industry" \
  -H "$HEADERS" -w "\nHTTP Status: %{http_code}\n"

# 4. 无效同步模式
echo "4. 无效同步模式..."
curl -X POST "$BASE_URL/knowledge-graph/sync" \
  -H "$HEADERS" \
  -d '{"mode": "invalid", "target": "stock"}' \
  -w "\nHTTP Status: %{http_code}\n"

echo "=== 错误测试完成 ==="
```

---

## 6. 性能测试

### 6.1 批量查询测试

```bash
#!/bin/bash

BASE_URL="http://localhost:8000/api/v1"
HEADERS="Content-Type: application/json"

# 测试股票列表
STOCKS=("000001.SZ" "601398.SH" "000002.SZ" "600036.SH" "600519.SH")

echo "=== 批量查询性能测试 ==="

for stock in "${STOCKS[@]}"; do
    echo "查询 $stock 的关系网络..."
    start_time=$(date +%s%N)
    
    curl -X GET "$BASE_URL/knowledge-graph/stocks/$stock/graph" \
      -H "$HEADERS" -s -o /dev/null
      
    end_time=$(date +%s%N)
    duration=$((($end_time - $start_time) / 1000000))
    echo "$stock 查询耗时: ${duration}ms"
done

echo "=== 性能测试完成 ==="
```

---

## 7. 注意事项

1. **环境准备**: 确保 Neo4j 和 PostgreSQL 服务正常运行
2. **数据同步**: 首次使用前需要先执行数据同步操作
3. **权限控制**: 生产环境应添加适当的认证和授权
4. **错误处理**: 所有 curl 命令应检查 HTTP 状态码
5. **数据格式**: JSON 请求体需要正确转义特殊字符

## 8. 调试技巧

```bash
# 查看详细响应头
curl -v -X GET "$BASE_URL/knowledge-graph/stocks/000001.SZ/neighbors?dimension=industry"

# 保存响应到文件
curl -X GET "$BASE_URL/knowledge-graph/stocks/000001.SZ/graph" \
  -H "$HEADERS" -o response.json

# 格式化 JSON 输出
curl -X GET "$BASE_URL/knowledge-graph/stocks/000001.SZ/graph" \
  -H "$HEADERS" | jq .

# 测试超时设置
curl -X GET "$BASE_URL/knowledge-graph/stocks/000001.SZ/graph" \
  -H "$HEADERS" --max-time 30
```

---

*本文档涵盖了知识图谱 API 的所有主要功能测试场景。如需更多测试用例或遇到问题，请参考 API 文档或联系开发团队。*
