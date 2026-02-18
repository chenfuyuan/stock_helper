# Data Engineering 模块 HTTP 接口文档

## 财务数据增量同步接口

### 接口信息
- **路径**: `POST /api/v1/sync/finance/incremental`
- **描述**: 财务数据增量同步（日常操作）
- **用途**: 用于定期同步最新披露的财务数据

### 请求参数

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| actual_date | string | 否 | 当天 | 指定同步日期 (YYYYMMDD) |

### 请求示例

```bash
# 使用默认日期（今天）
curl -X POST "http://localhost:8000/api/v1/sync/finance/incremental"

# 指定日期
curl -X POST "http://localhost:8000/api/v1/sync/finance/incremental" \
     -H "Content-Type: application/json" \
     -d '{"actual_date": "20250218"}'
```

### 响应格式

```json
{
  "success": true,
  "code": "FINANCE_INCREMENTAL_SYNC_SUCCESS",
  "message": "财务数据增量同步成功",
  "data": {
    "status": "success",
    "synced_count": 25,
    "failed_count": 2,
    "retry_count": 5,
    "retry_success_count": 3,
    "target_period": "20241231",
    "message": "成功同步 25 只股票，失败 2 只；重试 5 条记录，成功 3 条"
  }
}
```

### 响应字段说明

| 字段名 | 类型 | 说明 |
|--------|------|------|
| success | boolean | 请求是否成功 |
| code | string | 响应代码 |
| message | string | 响应消息 |
| data.status | string | 同步状态 |
| data.synced_count | integer | 成功同步的股票数量 |
| data.failed_count | integer | 同步失败的股票数量 |
| data.retry_count | integer | 重试次数 |
| data.retry_success_count | integer | 重试成功的次数 |
| data.target_period | string | 目标报告期 |
| data.message | string | 详细同步结果说明 |

### 同步策略

该接口采用多策略同步机制：

1. **策略 A（高优先级）**: 今日披露名单驱动
2. **策略 B（低优先级）**: 长尾轮询补齐缺失数据
3. **策略 C（前置步骤）**: 失败重试机制

### 注意事项

- 财务数据同步通常需要较长时间，建议设置较长的超时时间
- 同步过程会自动处理失败重试，无需手动干预
- 建议在交易日结束后执行此接口
- 可通过调度器配置自动执行（每天凌晨 0 点）

## 其他相关接口

### 财务历史全量同步
- **路径**: `POST /api/v1/sync/finance/full`
- **用途**: 初始化或数据修复时的全量同步

### 日线增量同步
- **路径**: `POST /api/v1/sync/daily/incremental`
- **用途**: 股票日线数据增量同步

### 股票基础信息同步
- **路径**: `POST /api/v1/sync`
- **用途**: 股票基础列表同步
