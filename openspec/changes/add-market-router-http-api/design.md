## Context

当前 `data_engineering` 模块已有完整的市场数据同步 Command 层，包括：
- `SyncAkShareMarketDataCmd`：统一同步5个市场数据（涨停池、炸板池、昨日涨停、龙虎榜、板块资金流向）
- 5个独立的同步 Command：`SyncLimitUpPoolCmd`、`SyncBrokenBoardCmd`、`SyncPreviousLimitUpCmd`、`SyncDragonTigerCmd`、`SyncSectorCapitalFlowCmd`
- `SyncConceptDataCmd`：概念数据同步
- `DataEngineeringContainer`：依赖注入容器，已提供所有 Command 的组装方法
- 已有 `stock_routes.py` 作为参考模板

但这些同步能力目前只能通过调度任务或 CLI 触发，缺少 HTTP 接口供外部系统或用户手动触发。

## Goals / Non-Goals

**Goals:**
- 创建 `market_router.py` 提供市场数据同步的 HTTP API
- 提供1个统一同步接口（同步5个市场数据）
- 提供5个分别同步接口（每个市场数据单独同步）
- 提供1个概念数据同步接口
- 遵循现有 FastAPI 架构和 DDD 分层
- 复用现有 Command 层和 Container，不修改领域逻辑
- 统一的响应格式，包含同步结果摘要

**Non-Goals:**
- 不修改现有的 Command 层逻辑
- 不添加新的数据同步功能
- 不实现认证授权（复用现有机制）
- 不实现异步后台任务（同步调用）

## Decisions

### 1. API 路径设计

**决策：** 使用 `/api/data-engineering/market/` 作为路由前缀

**理由：**
- 遵循现有 `stock_routes.py` 的路径风格
- 清晰标识所属模块和功能域

**备选方案：**
- `/api/market/sync/` - 不够清晰模块归属
- `/api/data-engineering/sync/market/` - 路径过长

### 2. 接口清单

| 方法 | 路径 | 功能 | 说明 |
|------|------|------|------|
| POST | `/sync/akshare` | 统一同步5个市场数据 | 调用 `SyncAkShareMarketDataCmd` |
| POST | `/sync/limit-up-pool` | 同步涨停池 | 调用 `SyncLimitUpPoolCmd` |
| POST | `/sync/broken-board` | 同步炸板池 | 调用 `SyncBrokenBoardCmd` |
| POST | `/sync/previous-limit-up` | 同步昨日涨停 | 调用 `SyncPreviousLimitUpCmd` |
| POST | `/sync/dragon-tiger` | 同步龙虎榜 | 调用 `SyncDragonTigerCmd` |
| POST | `/sync/sector-capital-flow` | 同步板块资金流向 | 调用 `SyncSectorCapitalFlowCmd` |
| POST | `/sync/concept` | 同步概念数据 | 调用 `SyncConceptDataCmd` |

### 3. 请求参数设计

**决策：** 
- 市场数据同步接口使用 `trade_date` 查询参数（格式：YYYY-MM-DD），默认为当天
- 概念数据同步接口无需参数

**理由：**
- 与现有 Command 接口保持一致
- 简化客户端使用

### 4. 响应格式设计

**决策：**
- 统一使用 `BaseResponse` 包装
- 市场数据统一同步使用 `AkShareSyncResult`
- 单个市场数据同步使用简单的 `{count, message}` 格式
- 概念数据同步使用 `ConceptSyncResult`

**理由：**
- 复用现有的 DTO，避免重复定义
- 保持响应格式一致性

### 5. 依赖注入方式

**决策：** 参考 `market_insight_router.py`，使用 `DataEngineeringContainer` 作为统一入口

**理由：**
- Container 已提供所有 Command 的组装方法
- 保持与项目其他模块一致的依赖注入风格

**实现示例：**
```python
async def get_container(
    session: AsyncSession = Depends(get_db_session),
) -> DataEngineeringContainer:
    return DataEngineeringContainer(session)
```

## Risks / Trade-offs

### Risk 1: 同步请求超时
**风险：** 统一同步接口可能耗时较长，导致 HTTP 请求超时
**缓解：**
- 接口文档中明确说明预期耗时
- 建议单个数据同步使用分别同步接口
- 未来可考虑添加异步后台任务模式

### Risk 2: 错误隔离
**风险：** 统一同步接口中单个数据失败不影响其他（Command 层已实现）
**缓解：**
- Command 层已有错误隔离机制
- 响应中包含 `errors` 字段明确告知失败信息

### Trade-off: 同步 vs 异步
**选择：** 同步调用（立即返回结果）
**理由：**
- 简单直接，符合现有接口风格
- 数据同步通常在秒级完成
- 未来可根据需要添加异步版本
