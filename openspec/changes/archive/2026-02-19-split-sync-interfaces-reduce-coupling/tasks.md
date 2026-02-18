## 1. 新增专用 Request DTO

- [x] 1.1 在 `graph_api_dtos.py` 中新增 `SyncStocksFullRequest` 模型
- [x] 1.2 在 `graph_api_dtos.py` 中新增 `SyncStocksIncrementalRequest` 模型
- [x] 1.3 在 `graph_api_dtos.py` 中新增 `SyncConceptsRequest` 模型
- [x] 1.4 在 `graph_api_dtos.py` 中新增 `SyncAllRequest` 模型

## 2. 新增专用路由端点

- [x] 2.1 在 `graph_router.py` 中新增 `POST /sync/stocks/full` 端点
- [x] 2.2 在 `graph_router.py` 中新增 `POST /sync/stocks/incremental` 端点
- [x] 2.3 在 `graph_router.py` 中新增 `POST /sync/concepts` 端点
- [x] 2.4 在 `graph_router.py` 中新增 `POST /sync/all` 端点

## 3. 实现新端点处理逻辑

- [x] 3.1 实现股票全量同步端点的处理逻辑
- [x] 3.2 实现股票增量同步端点的处理逻辑
- [x] 3.3 实现概念同步端点的处理逻辑
- [x] 3.4 实现全部同步端点的处理逻辑
- [x] 3.5 提取公共处理逻辑到私有辅助函数，避免代码重复

## 4. 更新原接口

- [x] 4.1 将原 `/sync` 接口标记为 deprecated
- [x] 4.2 确保原接口内部逻辑转发到新的处理函数（保持向后兼容）

## 5. 验证与测试

- [x] 5.1 验证所有新端点能正常工作
- [x] 5.2 验证原接口仍能正常工作（向后兼容）
- [x] 5.3 验证 OpenAPI 文档正确显示 deprecated 标记
