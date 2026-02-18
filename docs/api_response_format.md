# API 响应格式统一化文档

## 概述

本项目已统一所有 REST API 接口的响应格式，使用 `BaseResponse[T]` 作为标准响应结构。

## 统一响应格式

### 成功响应格式

```json
{
  "success": true,
  "code": "OPERATION_SUCCESS",
  "message": "操作成功完成",
  "data": {
    // 具体的业务数据
  }
}
```

### 错误响应格式

```json
{
  "success": false,
  "code": "ERROR_CODE",
  "message": "错误描述信息"
}
```

## 响应字段说明

| 字段名 | 类型 | 说明 |
|--------|------|------|
| success | boolean | 请求是否成功 |
| code | string | 响应代码，用于前端逻辑判断 |
| message | string | 响应消息描述 |
| data | T | 业务返回数据，成功时包含具体数据，错误时为 null |

## 已统一化的模块

- ✅ Coordinator 模块 - 研究编排和会话管理接口
- ✅ LLM Platform 模块 - 搜索、聊天和配置管理接口
- ✅ Knowledge Center 模块 - 图谱查询接口
- ✅ Research 模块 - 研究分析接口
- ✅ Debate 模块 - 辩论接口
- ✅ Judge 模块 - 裁决接口
- ✅ Foundation 模块 - 调度器接口
- ✅ Market Insight 模块 - 市场洞察接口

## 响应代码规范

### 成功响应代码

- `RESEARCH_ORCHESTRATION_SUCCESS` - 研究编排成功
- `WEB_SEARCH_SUCCESS` - Web 搜索成功
- `LLM_CHAT_SUCCESS` - LLM 聊天成功
- `STOCK_NEIGHBORS_SUCCESS` - 同维度股票查询成功
- `STOCK_GRAPH_SUCCESS` - 个股关系网络查询成功
- `GRAPH_SYNC_SUCCESS` - 图谱数据同步成功
- `TECHNICAL_ANALYSIS_SUCCESS` - 技术分析成功
- `VALUATION_MODEL_SUCCESS` - 估值建模成功
- `FINANCIAL_AUDIT_SUCCESS` - 财务审计成功
- `CATALYST_DETECTIVE_SUCCESS` - 催化剂侦探分析成功
- `MACRO_INTELLIGENCE_SUCCESS` - 宏观情报分析成功
- `DEBATE_RUN_SUCCESS` - 辩论执行成功
- `JUDGE_VERDICT_SUCCESS` - 投资裁决成功
- `SCHEDULER_STATUS_SUCCESS` - 调度器状态查询成功
- `CONCEPT_HEAT_SUCCESS` - 概念热度查询成功
- `LIMIT_UP_SUCCESS` - 涨停股查询成功
- `DAILY_REPORT_SUCCESS` - 每日复盘报告生成成功
- `SENTIMENT_METRICS_SUCCESS` - 市场情绪指标查询成功
- `CAPITAL_FLOW_SUCCESS` - 资金流向分析查询成功

### 错误响应代码

- `INTERNAL_SERVER_ERROR` - 服务器内部错误
- `VALIDATION_ERROR` - 参数验证错误
- `NOT_FOUND` - 资源不存在
- `PERMISSION_DENIED` - 权限不足

## 前端集成指南

### 处理成功响应

```javascript
// 处理 API 响应的通用函数
function handleApiResponse(response) {
  if (response.success) {
    // 成功处理逻辑
    console.log('操作成功:', response.message);
    return response.data;
  } else {
    // 错误处理逻辑
    console.error('操作失败:', response.message);
    throw new Error(response.message);
  }
}

// 使用示例
fetch('/api/research', {
  method: 'POST',
  body: JSON.stringify(requestData)
})
.then(response => response.json())
.then(handleApiResponse)
.then(data => {
  // 使用业务数据
  console.log('研究结果:', data);
})
.catch(error => {
  // 处理错误
  console.error('请求失败:', error);
});
```

### 错误处理

```javascript
// 错误处理中间件
function errorHandler(error) {
  if (error.response) {
    const { success, code, message } = error.response.data;
    if (!success) {
      // 根据错误码进行不同处理
      switch (code) {
        case 'VALIDATION_ERROR':
          showValidationError(message);
          break;
        case 'NOT_FOUND':
          showNotFoundError(message);
          break;
        case 'INTERNAL_SERVER_ERROR':
          showServerError(message);
          break;
        default:
          showGenericError(message);
      }
    }
  }
}
```

## 迁移说明

### 旧格式到新格式的迁移

**旧格式**:
```json
{
  "symbol": "000001.SZ",
  "status": "completed",
  "data": {...}
}
```

**新格式**:
```json
{
  "success": true,
  "code": "RESEARCH_ORCHESTRATION_SUCCESS",
  "message": "研究编排成功完成",
  "data": {
    "symbol": "000001.SZ",
    "status": "completed",
    "data": {...}
  }
}
```

### 迁移步骤

1. 更新前端 API 调用代码，添加响应格式检查
2. 修改数据处理逻辑，从 `response.data` 中获取业务数据
3. 更新错误处理逻辑，使用统一的错误格式
4. 测试所有接口调用，确保功能正常

## 注意事项

1. 所有接口的响应数据都被包装在 `data` 字段中
2. 错误响应统一使用 `success: false` 格式
3. 响应代码用于前端逻辑判断，建议根据不同代码进行相应的 UI 处理
4. 保持向后兼容性，逐步迁移现有代码
