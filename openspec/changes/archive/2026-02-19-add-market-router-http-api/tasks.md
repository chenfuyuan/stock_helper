## 1. 创建 Market Router 文件

- [x] 1.1 创建 `src/modules/data_engineering/presentation/rest/market_router.py` 文件
- [x] 1.2 定义 APIRouter，prefix 为 `/data-engineering/market`，tag 为 `Market Data Sync`
- [x] 1.3 实现依赖注入函数 `get_container`，返回 `DataEngineeringContainer` 实例

## 2. 实现统一同步接口

- [x] 2.1 实现 `POST /sync/akshare` 接口，调用 `SyncAkShareMarketDataCmd`
- [x] 2.2 定义请求参数 `trade_date`（可选，默认当天）
- [x] 2.3 定义响应模型，使用 `BaseResponse[AkShareSyncResult]`

## 3. 实现单个市场数据同步接口

- [x] 3.1 实现 `POST /sync/limit-up-pool` 接口，调用 `SyncLimitUpPoolCmd`
- [x] 3.2 实现 `POST /sync/broken-board` 接口，调用 `SyncBrokenBoardCmd`
- [x] 3.3 实现 `POST /sync/previous-limit-up` 接口，调用 `SyncPreviousLimitUpCmd`
- [x] 3.4 实现 `POST /sync/dragon-tiger` 接口，调用 `SyncDragonTigerCmd`
- [x] 3.5 实现 `POST /sync/sector-capital-flow` 接口，调用 `SyncSectorCapitalFlowCmd`
- [x] 3.6 为单个数据同步接口定义统一的响应模型（包含 count 和 message）

## 4. 实现概念数据同步接口

- [x] 4.1 实现 `POST /sync/concept` 接口，调用 `SyncConceptDataCmd`
- [x] 4.2 定义响应模型，使用 `BaseResponse[ConceptSyncResult]`

## 5. 注册路由

- [x] 5.1 在 `src/modules/data_engineering/presentation/rest/__init__.py` 中导入 `market_router`
- [x] 5.2 将 `market_router` 注册到 `router` 中

## 6. 验证与测试

- [x] 6.1 验证所有路由已正确注册
- [x] 6.2 验证接口文档可访问（Swagger UI）
- [x] 6.3 运行代码检查，确保无类型错误和 lint 错误
