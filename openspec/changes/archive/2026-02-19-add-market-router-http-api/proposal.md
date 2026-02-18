## Why

目前市场行情数据同步功能只能通过调度任务或 CLI 触发，缺乏通过 HTTP 接口手动触发的能力。为了提供更灵活的数据同步方式，需要开发一系列 HTTP 接口，允许用户通过 API 调用触发市场行情数据和概念数据的同步。

## What Changes

- 新增 `market_router.py` 路由文件，位于 `data_engineering/presentation/rest/` 目录
- 提供 AkShare 市场数据同步接口（包含五个子数据：涨停池、炸板池、昨日涨停、龙虎榜、板块资金流向）
- 提供概念数据同步接口
- 遵循项目现有 FastAPI 路由架构和 DDD 分层设计
- 使用依赖注入模式，通过 `DataEngineeringContainer` 获取 Command 实例
- 统一的响应格式，包含同步结果摘要

## Capabilities

### New Capabilities
- `market-data-sync-api`: 提供市场行情数据同步的 HTTP API 接口，包括 AkShare 市场数据和概念数据的同步触发能力

### Modified Capabilities
- 无

## Impact

- 受影响代码：`src/modules/data_engineering/presentation/rest/` 目录下新增路由文件
- API：新增 `/api/data-engineering/market/sync/akshare` 和 `/api/data-engineering/market/sync/concept` 等端点
- 依赖：复用现有 `DataEngineeringContainer` 和 Command 层，无新增外部依赖
- 系统：遵循现有架构模式，不改变领域层和应用层逻辑
