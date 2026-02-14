## 1. 数据库 Schema 与领域模型扩展

- [x] 1.1 `ResearchSession` 领域实体新增 `retry_count: int = 0` 和 `parent_session_id: UUID | None = None` 字段
- [x] 1.2 `ResearchSessionModel` ORM 模型新增 `retry_count`（Integer, default 0）和 `parent_session_id`（UUID, nullable, FK → research_sessions.id）列
- [x] 1.3 仓储映射函数 `_session_model_to_entity` / `_session_entity_to_model` 补充新字段转换
- [x] 1.4 创建 Alembic migration：research_sessions 表新增 `retry_count` 和 `parent_session_id` 列

## 2. Domain DTO 扩展

- [x] 2.1 `ResearchRequest` 新增可选字段 `pre_populated_results: dict[str, Any] | None = None`、`parent_session_id: UUID | None = None`、`retry_count: int = 0`
- [x] 2.2 `ResearchResult` 新增字段 `retry_count: int = 0`
- [x] 2.3 新增领域异常类型：`SessionNotFoundError`、`SessionNotRetryableError`（状态为 completed 或 running 时拒绝重试）

## 3. 编排器支持 pre_populated_results

- [x] 3.1 `LangGraphResearchOrchestrator.run()` 中读取 `request.pre_populated_results`，非 None 时预填充 `initial_state["results"]`
- [x] 3.2 `LangGraphResearchOrchestrator.run()` 中使用 `request.parent_session_id` 和 `request.retry_count` 创建子 session（parent_session_id 和 retry_count 写入 ResearchSession）
- [x] 3.3 `ResearchResult` 返回值中填充 `retry_count`

## 4. Application 层重试用例

- [x] 4.1 `ResearchOrchestrationService` 新增 `retry(session_id: UUID, skip_debate: bool = False) -> ResearchResult` 方法
- [x] 4.2 `retry()` 实现：查询源 session → 校验状态 → 查询 NodeExecution → 分离成功/失败专家 → 提取 pre_populated_results → 构建 ResearchRequest → 委托 Port 执行

## 5. Presentation 层 REST 端点

- [x] 5.1 `ResearchOrchestrationResponse` 新增 `retry_count: int = 0` 字段
- [x] 5.2 新增 `POST /api/v1/coordinator/research/{session_id}/retry` 路由，解析路径参数和请求体，调用 `service.retry()`
- [x] 5.3 路由异常处理：SessionNotFoundError → 404、SessionNotRetryableError（completed）→ 400、SessionNotRetryableError（running）→ 409、AllExpertsFailedError → 500
- [x] 5.4 在 `src/api/routes.py` 中注册新路由（如需单独注册）

## 6. 测试

- [x] 6.1 单元测试：`retry()` 方法 — session 不存在抛异常
- [x] 6.2 单元测试：`retry()` 方法 — session 状态为 completed / running 时拒绝重试
- [x] 6.3 单元测试：`retry()` 方法 — 正确分离成功/失败专家，构建含 pre_populated_results 的 ResearchRequest
- [x] 6.4 单元测试：编排器 — pre_populated_results 注入图初始状态，仅失败专家被执行
- [x] 6.5 单元测试：编排器 — pre_populated_results 为 None 时行为不变
- [x] 6.6 集成测试：POST /research/{session_id}/retry — 对 partial session 重试后返回完整结果
- [x] 6.7 集成测试：POST /research/{session_id}/retry — 404 / 400 / 409 错误码
- [x] 6.8 单元测试：ResearchResult / ResearchOrchestrationResponse 包含 retry_count 字段
