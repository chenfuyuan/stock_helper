---
title: Market Data Sync API Specification
version: 1.0
last_updated: 2026-02-19
module: data_engineering
capabilities:
  - market-data-sync-api
source_specs:
  - market-data-sync-api
---

# Market Data Sync API Specification

## Purpose

`market-data-sync-api` 能力为 `data_engineering` 模块提供 HTTP API 接口，允许通过 HTTP 请求触发市场行情数据和概念数据的同步操作。

## Capabilities

| Capability | Description | Source |
|------------|-------------|--------|
| market-data-sync-api | 市场行情数据同步 HTTP API | market-data-sync-api |

---

## capability: market-data-sync-api

`market-data-sync-api` 提供市场行情数据同步的 REST API 接口，包括统一同步接口和分别同步接口。

---

## ADDED Requirements

### Requirement: Market Router 创建

系统 SHALL 在 `src/modules/data_engineering/presentation/rest/market_router.py` 中创建 FastAPI 路由模块，提供市场数据同步接口。

该路由 SHALL 使用 prefix `/data-engineering/market`，tag 为 `Market Data Sync`。

#### Scenario: 路由文件创建
- **WHEN** 检查 `data_engineering/presentation/rest/` 目录
- **THEN**  SHALL 存在 `market_router.py` 文件
- **THEN** 该文件 SHALL 定义 `APIRouter` 实例，prefix 为 `/data-engineering/market`

---

### Requirement: 依赖注入容器

系统 SHALL 在 `market_router.py` 中定义依赖注入函数，通过 `DataEngineeringContainer` 获取 Command 实例。

该函数 SHALL 接受 `AsyncSession` 依赖，返回 `DataEngineeringContainer` 实例。

#### Scenario: 容器依赖注入
- **WHEN** 检查 `market_router.py` 中的依赖注入函数
- **THEN**  SHALL 存在 `get_container` 函数
- **THEN** 该函数 SHALL 使用 `Depends(get_db_session)` 获取数据库会话
- **THEN** 该函数 SHALL 返回 `DataEngineeringContainer(session)` 实例

---

### Requirement: AkShare 统一同步接口

系统 SHALL 提供 `POST /api/data-engineering/market/sync/akshare` 接口，用于统一同步5个市场数据。

该接口 SHALL：
- 接受可选查询参数 `trade_date`（格式：YYYY-MM-DD），默认为当天
- 调用 `SyncAkShareMarketDataCmd.execute(trade_date)`
- 返回 `BaseResponse[AkShareSyncResult]` 格式响应

#### Scenario: 统一同步成功
- **WHEN** 客户端调用 `POST /api/data-engineering/market/sync/akshare`
- **THEN** 系统 SHALL 调用 `SyncAkShareMarketDataCmd` 执行同步
- **THEN** 系统 SHALL 返回包含 `AkShareSyncResult` 的成功响应

#### Scenario: 指定日期同步
- **WHEN** 客户端调用 `POST /api/data-engineering/market/sync/akshare?trade_date=2026-02-18`
- **THEN** 系统 SHALL 使用指定日期 `2026-02-18` 执行同步

---

### Requirement: 涨停池同步接口

系统 SHALL 提供 `POST /api/data-engineering/market/sync/limit-up-pool` 接口，用于单独同步涨停池数据。

该接口 SHALL：
- 接受可选查询参数 `trade_date`（格式：YYYY-MM-DD），默认为当天
- 调用 `SyncLimitUpPoolCmd.execute(trade_date)`
- 返回 `BaseResponse` 格式响应，包含 `count` 和 `message` 字段

#### Scenario: 涨停池同步成功
- **WHEN** 客户端调用 `POST /api/data-engineering/market/sync/limit-up-pool`
- **THEN** 系统 SHALL 调用 `SyncLimitUpPoolCmd` 执行同步
- **THEN** 系统 SHALL 返回包含同步条数的成功响应

---

### Requirement: 炸板池同步接口

系统 SHALL 提供 `POST /api/data-engineering/market/sync/broken-board` 接口，用于单独同步炸板池数据。

该接口 SHALL：
- 接受可选查询参数 `trade_date`（格式：YYYY-MM-DD），默认为当天
- 调用 `SyncBrokenBoardCmd.execute(trade_date)`
- 返回 `BaseResponse` 格式响应，包含 `count` 和 `message` 字段

#### Scenario: 炸板池同步成功
- **WHEN** 客户端调用 `POST /api/data-engineering/market/sync/broken-board`
- **THEN** 系统 SHALL 调用 `SyncBrokenBoardCmd` 执行同步
- **THEN** 系统 SHALL 返回包含同步条数的成功响应

---

### Requirement: 昨日涨停同步接口

系统 SHALL 提供 `POST /api/data-engineering/market/sync/previous-limit-up` 接口，用于单独同步昨日涨停表现数据。

该接口 SHALL：
- 接受可选查询参数 `trade_date`（格式：YYYY-MM-DD），默认为当天
- 调用 `SyncPreviousLimitUpCmd.execute(trade_date)`
- 返回 `BaseResponse` 格式响应，包含 `count` 和 `message` 字段

#### Scenario: 昨日涨停同步成功
- **WHEN** 客户端调用 `POST /api/data-engineering/market/sync/previous-limit-up`
- **THEN** 系统 SHALL 调用 `SyncPreviousLimitUpCmd` 执行同步
- **THEN** 系统 SHALL 返回包含同步条数的成功响应

---

### Requirement: 龙虎榜同步接口

系统 SHALL 提供 `POST /api/data-engineering/market/sync/dragon-tiger` 接口，用于单独同步龙虎榜数据。

该接口 SHALL：
- 接受可选查询参数 `trade_date`（格式：YYYY-MM-DD），默认为当天
- 调用 `SyncDragonTigerCmd.execute(trade_date)`
- 返回 `BaseResponse` 格式响应，包含 `count` 和 `message` 字段

#### Scenario: 龙虎榜同步成功
- **WHEN** 客户端调用 `POST /api/data-engineering/market/sync/dragon-tiger`
- **THEN** 系统 SHALL 调用 `SyncDragonTigerCmd` 执行同步
- **THEN** 系统 SHALL 返回包含同步条数的成功响应

---

### Requirement: 板块资金流向同步接口

系统 SHALL 提供 `POST /api/data-engineering/market/sync/sector-capital-flow` 接口，用于单独同步板块资金流向数据。

该接口 SHALL：
- 接受可选查询参数 `trade_date`（格式：YYYY-MM-DD），默认为当天
- 调用 `SyncSectorCapitalFlowCmd.execute(trade_date)`
- 返回 `BaseResponse` 格式响应，包含 `count` 和 `message` 字段

#### Scenario: 板块资金流向同步成功
- **WHEN** 客户端调用 `POST /api/data-engineering/market/sync/sector-capital-flow`
- **THEN** 系统 SHALL 调用 `SyncSectorCapitalFlowCmd` 执行同步
- **THEN** 系统 SHALL 返回包含同步条数的成功响应

---

### Requirement: 概念数据同步接口

系统 SHALL 提供 `POST /api/data-engineering/market/sync/concept` 接口，用于同步概念数据。

该接口 SHALL：
- 无需查询参数
- 调用 `SyncConceptDataCmd.execute()`
- 返回 `BaseResponse[ConceptSyncResult]` 格式响应

#### Scenario: 概念数据同步成功
- **WHEN** 客户端调用 `POST /api/data-engineering/market/sync/concept`
- **THEN** 系统 SHALL 调用 `SyncConceptDataCmd` 执行同步
- **THEN** 系统 SHALL 返回包含 `ConceptSyncResult` 的成功响应

---

### Requirement: 路由注册

系统 SHALL 将 `market_router` 注册到主 FastAPI 应用中。

#### Scenario: 路由已注册
- **WHEN** 检查主应用路由注册
- **THEN** `market_router` SHALL 已被包含在应用路由中
