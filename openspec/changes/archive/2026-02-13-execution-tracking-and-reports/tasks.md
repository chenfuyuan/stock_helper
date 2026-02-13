## 1. Shared Infrastructure — ExecutionContext

- [x] 1.1 创建 `src/shared/infrastructure/execution_context.py`：定义 `ExecutionContext`（Pydantic BaseModel，含 `session_id: str`）和 `current_execution_ctx: ContextVar[ExecutionContext | None]`（默认 None）

## 2. Database Migration

- [x] 2.1 创建 Alembic migration：新增 `research_sessions` 表（id UUID PK, symbol, status, selected_experts JSONB, options JSONB, trigger_source, created_at, completed_at, duration_ms）
- [x] 2.2 同一 migration 新增 `node_executions` 表（id UUID PK, session_id FK, node_type, status, result_data JSONB, narrative_report TEXT, error_type, error_message TEXT, started_at, completed_at, duration_ms）
- [x] 2.3 同一 migration 新增 `llm_call_logs` 表（id UUID PK, session_id nullable, caller_module, caller_agent, model_name, vendor, prompt_text TEXT, system_message TEXT, completion_text TEXT, prompt_tokens, completion_tokens, total_tokens, temperature, latency_ms, status, error_message TEXT, created_at）
- [x] 2.4 同一 migration 新增 `external_api_call_logs` 表（id UUID PK, session_id nullable, service_name, operation, request_params JSONB, response_data TEXT, status_code, latency_ms, status, error_message TEXT, created_at）
- [x] 2.5 添加索引：research_sessions(symbol, created_at)、node_executions(session_id)、llm_call_logs(session_id, created_at)、external_api_call_logs(session_id, created_at)
- [x] 2.6 更新 `alembic/env.py` 导入新增的 ORM Model，确保 autogenerate 可检测

## 3. Pipeline Execution Tracking — 领域层与持久层（Coordinator）

- [x] 3.1 创建 `coordinator/domain/model/research_session.py`：`ResearchSession` 实体（Pydantic BaseModel），含状态转换方法（`complete()`, `fail()`, `mark_partial()`）
- [x] 3.2 创建 `coordinator/domain/model/node_execution.py`：`NodeExecution` 实体，含 `mark_success(result_data, narrative_report)` 和 `mark_failed(error_type, error_message)` 方法
- [x] 3.3 创建 `coordinator/domain/ports/research_session_repository.py`：`IResearchSessionRepository` Port（ABC），定义 `save_session`、`update_session`、`save_node_execution`、`get_session_by_id`、`list_sessions`、`get_node_executions_by_session` 方法
- [x] 3.4 创建 `coordinator/infrastructure/persistence/research_session_model.py`：SQLAlchemy ORM Model `ResearchSessionModel`
- [x] 3.5 创建 `coordinator/infrastructure/persistence/node_execution_model.py`：SQLAlchemy ORM Model `NodeExecutionModel`
- [x] 3.6 创建 `coordinator/infrastructure/persistence/research_session_repository.py`：`PgResearchSessionRepository` 实现 `IResearchSessionRepository`

## 4. LLM Call Audit — 领域层与持久层（llm_platform）

- [x] 4.1 创建 `llm_platform/domain/dtos/llm_call_log_dtos.py`：`LLMCallLog` DTO（Pydantic BaseModel）
- [x] 4.2 创建 `llm_platform/domain/ports/llm_call_log_repository.py`：`ILLMCallLogRepository` Port（ABC），定义 `save`、`get_by_session_id` 方法
- [x] 4.3 创建 `llm_platform/infrastructure/persistence/llm_call_log_model.py`：SQLAlchemy ORM Model `LLMCallLogModel`
- [x] 4.4 创建 `llm_platform/infrastructure/persistence/llm_call_log_repository.py`：`PgLLMCallLogRepository` 实现
- [x] 4.5 修改 `llm_platform/application/services/llm_service.py`：在 `generate()` 方法中添加调用计时、读取 ExecutionContext、构建 LLMCallLog 并通过 Repository 异步写入（try/except 包裹，写入失败记录 warning 不阻塞）
- [x] 4.6 创建 `llm_platform/application/queries/llm_call_log_query_service.py`：按 session_id 查询 LLM 调用日志的查询服务

## 5. External API Call Logging — 模型与拦截

- [x] 5.1 创建 `shared/infrastructure/persistence/external_api_call_log_model.py`：SQLAlchemy ORM Model `ExternalAPICallLogModel`（模型放 shared 供复用）
- [x] 5.2 创建 `shared/domain/ports/external_api_call_log_repository.py`：`IExternalAPICallLogRepository` Port
- [x] 5.3 创建 `shared/infrastructure/persistence/external_api_call_log_repository.py`：`PgExternalAPICallLogRepository` 实现
- [x] 5.4 修改 `llm_platform/application/services/web_search_service.py`：在 `search()` 方法中添加调用计时、读取 ExecutionContext、构建 ExternalAPICallLog 并异步写入（写入失败记录 warning 不阻塞）
- [x] 5.5 创建查询服务：按 session_id 查询外部 API 调用日志

## 6. LangGraph 编排层集成

- [x] 6.1 创建 `coordinator/infrastructure/orchestration/node_persistence_wrapper.py`：`persist_node_execution` 高阶函数，包装节点函数，记录 started_at → 执行 → 记录 result/error → 写入 NodeExecution（写入失败不阻塞）
- [x] 6.2 修改 `coordinator/infrastructure/orchestration/graph_builder.py`：在 `build_research_graph()` 中用 `persist_node_execution` 包装所有节点函数（专家、debate、judge）
- [x] 6.3 修改 `coordinator/infrastructure/orchestration/langgraph_orchestrator.py`：在 `run()` 方法中，执行 graph 前创建 ResearchSession + 设置 ExecutionContext，执行后更新 session 状态 + 重置 context（try/finally）
- [x] 6.4 修改 `coordinator/domain/dtos/research_dtos.py`：`ResearchResult` 新增 `session_id: str` 字段
- [x] 6.5 修改 `coordinator/presentation/rest/research_routes.py`：响应体新增 `session_id`

## 7. Agent Narrative Reports — Research 模块

- [x] 7.1 修改 `TechnicalAnalysisResultDTO`：新增 `narrative_report: str = ""` 字段
- [x] 7.2 修改 `FinancialAuditResultDTO`：新增 `narrative_report: str = ""` 字段
- [x] 7.3 修改 `ValuationResultDTO`：新增 `narrative_report: str = ""` 字段
- [x] 7.4 修改 `MacroIntelligenceResultDTO`：新增 `narrative_report: str = ""` 字段
- [x] 7.5 修改 `CatalystDetectiveResultDTO`：新增 `narrative_report: str = ""` 字段
- [x] 7.6 更新技术分析师 Agent Prompt：添加 narrative_report 输出要求（核心结论、论据、风险、置信度，中文）
- [x] 7.7 更新财务审计员 Agent Prompt：同上
- [x] 7.8 更新估值建模师 Agent Prompt：同上
- [x] 7.9 更新宏观情报员 Agent Prompt：同上
- [x] 7.10 更新催化剂侦探 Agent Prompt：同上
- [x] 7.11 更新 5 个 Research output_parser：解析 narrative_report 字段，缺失时默认空字符串

## 8. Agent Narrative Reports — Debate 模块

- [x] 8.1 修改 `BullArgument`：新增 `narrative_report: str = ""` 字段
- [x] 8.2 修改 `BearArgument`：新增 `narrative_report: str = ""` 字段
- [x] 8.3 修改 `ResolutionResult`：新增 `narrative_report: str = ""` 字段
- [x] 8.4 更新 Bull Advocate Agent Prompt：添加 narrative_report 输出要求
- [x] 8.5 更新 Bear Advocate Agent Prompt：同上
- [x] 8.6 更新 Resolution Agent Prompt：同上
- [x] 8.7 更新 3 个 Debate output_parser：解析 narrative_report 字段，缺失时默认空字符串

## 9. Agent Narrative Reports — Judge 模块

- [x] 9.1 修改 `VerdictResult`：新增 `narrative_report: str = ""` 字段
- [x] 9.2 更新 Judge Verdict Agent Prompt：添加 narrative_report 输出要求
- [x] 9.3 更新 Judge output_parser：解析 narrative_report 字段，缺失时默认空字符串

## 10. History Query API

- [x] 10.1 创建 `coordinator/application/queries/session_list_query.py`：会话列表查询用例（支持 symbol / 时间范围 / 分页）
- [x] 10.2 创建 `coordinator/application/queries/session_detail_query.py`：会话详情查询用例（含 NodeExecution 列表）
- [x] 10.3 创建 `coordinator/presentation/rest/session_routes.py`：`GET /research/sessions` 和 `GET /research/sessions/{session_id}` 端点
- [x] 10.4 创建 `coordinator/presentation/rest/session_routes.py`：`GET /research/sessions/{session_id}/llm-calls` 端点（调用 llm_platform 查询服务）
- [x] 10.5 创建 `coordinator/presentation/rest/session_routes.py`：`GET /research/sessions/{session_id}/api-calls` 端点（调用 shared 查询服务）
- [x] 10.6 定义响应 DTO（session 摘要、session 详情、llm-call 列表项、api-call 列表项）

## 11. DI Container 组装

- [x] 11.1 更新 `coordinator/container.py`：注册 `IResearchSessionRepository` → `PgResearchSessionRepository`，注入到 orchestrator
- [x] 11.2 更新 `llm_platform/container.py`：注册 `ILLMCallLogRepository` → `PgLLMCallLogRepository`，注入到 LLMService
- [x] 11.3 配置 `IExternalAPICallLogRepository` → `PgExternalAPICallLogRepository`，注入到 WebSearchService

## 12. 测试

- [x] 12.1 测试 ExecutionContext 设置/获取/重置/并行隔离
- [x] 12.2 测试 ResearchSession 生命周期（running → completed / partial / failed）
- [x] 12.3 测试 NodeExecution 成功记录与失败记录
- [x] 12.4 测试 LLMService 调用审计（成功、失败、无上下文降级）
- [x] 12.5 测试 WebSearchService 调用日志（成功、失败、无上下文降级）
- [x] 12.6 测试持久化写入失败不阻塞主流程
- [x] 12.7 测试 narrative_report 字段解析（正常 + 缺失降级）
- [x] 12.8 测试历史查询 API（列表筛选/分页、详情、404、空结果）
