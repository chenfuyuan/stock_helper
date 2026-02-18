## MODIFIED Requirements

### Requirement: 调度器响应格式
调度器模块的所有接口 SHALL 返回统一的 `BaseResponse[T]` 格式，确保与其他 API 接口响应格式的一致性。

#### Scenario: 调度任务创建响应
- **WHEN** 调度任务创建请求成功完成
- **THEN** 系统返回 `BaseResponse[SchedulerTaskResult]`，其中：
  - `success: true`
  - `message: "调度任务创建成功"`
  - `code: "SCHEDULER_TASK_CREATE_SUCCESS"`
  - `data: SchedulerTaskResult` 包含任务创建结果

#### Scenario: 调度任务查询响应
- **WHEN** 调度任务查询请求成功完成
- **THEN** 系统返回 `BaseResponse[SchedulerTaskInfo]`，其中：
  - `success: true`
  - `message: "调度任务查询成功"`
  - `code: "SCHEDULER_TASK_QUERY_SUCCESS"`
  - `data: SchedulerTaskInfo` 包含任务详细信息

#### Scenario: 调度任务执行响应
- **WHEN** 调度任务执行请求完成
- **THEN** 系统返回 `BaseResponse[SchedulerExecutionResult]`，其中：
  - `success: true`
  - `message: "调度任务执行成功"`
  - `code: "SCHEDULER_EXECUTION_SUCCESS"`
  - `data: SchedulerExecutionResult` 包含执行结果

#### Scenario: 调度器失败响应
- **WHEN** 调度器操作过程中发生错误
- **THEN** 系统返回 `ErrorResponse`，包含：
  - `success: false`
  - `message: str` 调度器操作失败的具体描述
  - `code: str` 对应的错误代码（如 "SCHEDULER_ERROR"、"TASK_EXECUTION_FAILED" 等）
