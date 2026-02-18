## Why

项目中存在不一致的 API 响应格式，部分接口使用了 `BaseResponse` 统一响应结构，而其他接口直接返回自定义模型或原始数据。这种不一致性导致：
- 前端处理逻辑复杂化，需要针对不同接口编写不同的响应解析代码
- 错误处理不统一，缺乏标准化的错误码和消息格式
- API 接口的可维护性和可扩展性降低
- 违反了项目技术规范中关于统一响应格式的要求

## What Changes

**BREAKING**: 将所有 REST API 接口统一使用 `BaseResponse[T]` 响应格式。

具体变更：
- 修改所有未使用 `BaseResponse` 的路由端点，使其返回 `BaseResponse[T]` 格式
- 更新所有自定义响应模型，将它们作为 `BaseResponse` 的泛型参数
- 统一错误处理，确保所有异常都通过 `BaseResponse` 的 `success=False` 格式返回
- 更新 API 文档和响应模型注解

## Capabilities

### New Capabilities
- `unify-api-response`: 统一所有 API 接口使用 BaseResponse 响应格式

### Modified Capabilities
- `data-engineering`: 市场数据同步接口响应格式统一化
- `coordinator`: 研究编排接口响应格式统一化  
- `llm-platform`: 搜索和聊天接口响应格式统一化
- `knowledge-center`: 图谱查询接口响应格式统一化
- `research`: 研究分析接口响应格式统一化
- `debate`: 辩论接口响应格式统一化
- `judge`: 裁决接口响应格式统一化
- `foundation`: 调度器接口响应格式统一化
- `market-insight`: 市场洞察接口响应格式统一化

## Impact

**受影响的代码**：
- 所有 `src/modules/*/presentation/rest/*.py` 路由文件
- 部分自定义响应模型和 DTO 类
- 错误处理中间件可能需要调整

**API 变更**：
- 所有接口的响应结构都会发生变化
- 响应数据会被包装在 `BaseResponse` 的 `data` 字段中
- 错误响应将使用统一的 `ErrorResponse` 格式

**依赖影响**：
- 无新增依赖
- 现有的 `BaseResponse` 和 `ErrorResponse` 类将被更广泛使用
- 可能需要更新相关的测试用例
