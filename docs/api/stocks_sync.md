# 股票数据同步 API 文档

## 1. 概述
本接口用于从 Tushare 财经数据接口获取 A 股股票列表基础数据，并将其清洗、转换为领域对象后同步至本地 PostgreSQL 数据库。

## 2. 接口定义

### 2.1 同步股票基础数据

*   **URL**: `/api/v1/stocks/sync`
*   **Method**: `POST`
*   **Auth**: 不需要 (暂无鉴权)
*   **Description**: 触发后台同步任务，拉取最新的股票列表信息 (包括代码、名称、行业、上市日期等) 并更新数据库。

#### 请求参数
无请求体参数。

#### 响应格式 (JSON)

**成功响应 (200 OK):**

```json
{
  "success": true,
  "code": "SYNC_SUCCESS",
  "message": "股票数据同步成功",
  "data": {
    "synced_count": 5000,
    "message": "Successfully synced 5000 stocks"
  }
}
```

**失败响应 (500 Internal Server Error):**

```json
{
  "success": false,
  "code": "TUSHARE_FETCH_ERROR",
  "message": "获取第三方股票数据失败",
  "details": "Connection timeout"
}
```

## 3. 数据结构说明

### StockInfo 领域对象

| 字段名 | 类型 | 说明 | 示例 |
| :--- | :--- | :--- | :--- |
| `third_code` | String | 第三方系统唯一代码 (Tushare ts_code) | `000001.SZ` |
| `symbol` | String | 股票代码 | `000001` |
| `name` | String | 股票名称 | `平安银行` |
| `area` | String | 所在地域 | `深圳` |
| `industry` | String | 所属行业 | `银行` |
| `market` | String | 市场类型 (主板/创业板/科创板) | `主板` |
| `list_date` | Date | 上市日期 | `1991-04-03` |

## 4. 开发与测试指南

### 4.1 环境变量配置
在 `.env` 文件中配置 Tushare Token:
```bash
TUSHARE_TOKEN=your_token_here
```

### 4.2 运行测试
```bash
pytest tests/application/test_sync_stocks.py
```
