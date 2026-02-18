## ADDED Requirements

### Requirement: 统一 API 响应格式
所有 REST API 接口 SHALL 使用 `BaseResponse[T]` 作为统一的响应格式，确保响应结构的一致性。

#### Scenario: 成功响应格式
- **WHEN** API 接口成功处理请求
- **THEN** 系统返回 `BaseResponse` 对象，包含：
  - `success: true`
  - `message: "Success"` 或具体的成功描述
  - `data: T` 包含实际的业务数据
  - `code: str` 可选的成功代码

#### Scenario: 错误响应格式
- **WHEN** API 接口处理过程中发生错误
- **THEN** 系统返回 `ErrorResponse` 对象，包含：
  - `success: false`
  - `message: str` 友好的错误提示
  - `code: str` 内部错误码

#### Scenario: 分页响应格式
- **WHEN** API 接口返回分页数据
- **THEN** 系统返回 `BaseResponse[PaginationResponse]`，其中 `PaginationResponse` 包含分页元数据

### Requirement: 响应模型类型注解更新
所有路由端点的 `response_model` 注解 SHALL 更新为使用 `BaseResponse[T]` 格式。

#### Scenario: 更新路由注解
- **WHEN** 开发者修改路由端点
- **THEN** 路由的 `response_model` 参数 SHALL 使用 `BaseResponse[具体数据类型]` 格式

#### Scenario: 保持类型安全
- **WHEN** 使用 `BaseResponse[T]` 泛型
- **THEN** 类型检查器能够正确推断响应数据的类型结构

### Requirement: 错误处理统一化
所有异常 SHALL 通过统一的错误处理机制转换为 `ErrorResponse` 格式。

#### Scenario: 业务异常处理
- **WHEN** 业务逻辑抛出预定义的业务异常
- **THEN** 错误处理中间件将其转换为对应的 `ErrorResponse`

#### Scenario: 系统异常处理
- **WHEN** 系统发生未预期的异常
- **THEN** 错误处理中间件将其转换为通用的 `ErrorResponse`，包含内部错误码

#### Scenario: HTTP 状态码映射
- **WHEN** 返回错误响应
- **THEN** HTTP 状态码 SHALL 正确反映错误类型（400、404、500 等）

### Requirement: 向后兼容性保证
在响应格式统一化过程中，所有业务逻辑 SHALL 保持不变，仅修改响应包装格式。

#### Scenario: 业务数据结构保持
- **WHEN** 响应格式统一化
- **THEN** 原始业务数据的结构和内容 SHALL 保持完全一致，仅被包装在 `BaseResponse.data` 字段中

#### Scenario: 接口路径保持
- **WHEN** 响应格式统一化
- **THEN** 所有接口的 URL 路径和 HTTP 方法 SHALL 保持不变
