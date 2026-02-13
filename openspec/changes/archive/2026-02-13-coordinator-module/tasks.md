## 1. 依赖与模块骨架

- [x] 1.1 在 `requirements.txt` 中添加 `langgraph` 依赖
- [x] 1.2 创建 `src/modules/coordinator/` 模块目录骨架：`__init__.py`、`container.py`、`application/__init__.py`、`application/dtos/__init__.py`、`domain/__init__.py`、`domain/model/__init__.py`、`domain/ports/__init__.py`、`infrastructure/__init__.py`、`infrastructure/adapters/__init__.py`、`infrastructure/orchestration/__init__.py`、`presentation/__init__.py`、`presentation/rest/__init__.py`
- [x] 1.3 验证：`docker compose exec app python -c "import src.modules.coordinator"` 正常执行

## 2. Domain 层 — 枚举、DTO、Port 接口、异常

- [x] 2.1 创建 `domain/model/enums.py`：定义 `ExpertType` 枚举（`TECHNICAL_ANALYST = "technical_analyst"` 等 5 个成员）
- [x] 2.2 创建 `domain/dtos/research_dtos.py`：定义 `ResearchRequest`（symbol + experts + options）、`ExpertResultItem`（expert_type + status + data + error）、`ResearchResult`（symbol + overall_status + expert_results）三个 Pydantic DTO
- [x] 2.3 创建 `domain/ports/research_expert_gateway.py`：定义 `IResearchExpertGateway`（ABC），包含 `run_expert(expert_type, symbol, options) -> dict[str, Any]` 抽象方法
- [x] 2.4 创建 `domain/ports/research_orchestration.py`：定义 `IResearchOrchestrationPort`（ABC），包含 `run(request: ResearchRequest) -> ResearchResult` 抽象方法
- [x] 2.5 创建 `domain/exceptions.py`：定义 Coordinator 领域异常（如 `AllExpertsFailedError`），继承 `src/shared/domain/exceptions.py` 中的 `AppException`

## 3. Infrastructure 层 — ResearchGatewayAdapter

- [x] 3.1 创建 `infrastructure/adapters/research_gateway_adapter.py`：实现 `IResearchExpertGateway`，注入 `ResearchContainer`，内部用 `match expert_type` 调度到对应的 Research Application Service
- [x] 3.2 实现催化剂侦探返回值归一化：`CatalystDetectiveAgentResult` → `dict[str, Any]`（`_normalize_catalyst_result` 方法）
- [x] 3.3 实现技术分析师的 `analysis_date` 参数解析（str → date）和 financial_auditor 的 `limit` 参数透传

## 4. Infrastructure 层 — LangGraph 编排图

- [x] 4.1 创建 `infrastructure/orchestration/graph_state.py`：定义 `ResearchGraphState`（TypedDict），包含 `symbol`、`selected_experts`、`options`、`results`（Annotated + merge_dicts reducer）、`errors`（Annotated + merge_dicts reducer）、`overall_status`
- [x] 4.2 创建 `infrastructure/orchestration/graph_builder.py`：实现 `build_research_graph(gateway: IResearchExpertGateway) -> CompiledGraph`，包含：通用节点工厂函数 `create_expert_node`、5 个专家节点注册、`Send` 路由函数、聚合节点、图编译
- [x] 4.3 实现路由函数：读取 `state["selected_experts"]`，为每个选中的专家返回 `Send(node_name, state)`
- [x] 4.4 实现聚合节点：检查 `results` 和 `errors`，设置 `overall_status`（completed / partial / failed）
- [x] 4.5 创建 `infrastructure/orchestration/langgraph_orchestrator.py`：实现 `LangGraphResearchOrchestrator(IResearchOrchestrationPort)`，接收 `IResearchExpertGateway`，在 `run()` 中构建图、将 `ResearchRequest` 转为初始 state、执行图、将最终 state 转为 `ResearchResult`

## 5. Application 层 — 编排服务

- [x] 5.1 创建 `application/research_orchestration_service.py`：实现 `ResearchOrchestrationService`，注入 `IResearchOrchestrationPort`，`execute()` 方法负责：校验 symbol 非空、校验 experts 非空且合法（全部在 ExpertType 中）、构建 `ResearchRequest`、调用 Port `run()`、根据 `overall_status` 返回结果或抛出异常

## 6. Presentation 层 — REST 路由

- [x] 6.1 创建 `presentation/rest/research_routes.py`：定义 Pydantic 请求模型（`ResearchOrchestrationRequest`）和响应模型（`ResearchOrchestrationResponse`），实现 `POST /research` 路由，通过 FastAPI `Depends` 装配服务
- [x] 6.2 实现异常处理：入参校验失败 → 400、`AllExpertsFailedError` → 500、未预期异常 → 500（记录日志）
- [x] 6.3 创建 `presentation/rest/__init__.py`：导出统一 `router`（prefix="/coordinator"）

## 7. Composition Root 与路由注册

- [x] 7.1 实现 `container.py`：定义 `CoordinatorContainer`，注入 `AsyncSession`，`research_orchestration_service()` 方法组装 `ResearchGatewayAdapter` → `LangGraphResearchOrchestrator` → `ResearchOrchestrationService`
- [x] 7.2 在 `src/api/routes.py` 中注册 Coordinator 路由：`api_router.include_router(coordinator_router)`
- [x] 7.3 验证：`docker compose exec app python -c "import src.main"` 正常启动，路由已注册

## 8. 测试

- [x] 8.1 创建 `tests/coordinator/` 目录和 `conftest.py`（mock `IResearchExpertGateway` 的 fixture）
- [x] 8.2 入参校验测试：symbol 缺失、experts 为空、experts 含非法值 → 校验异常
- [x] 8.3 按需路由测试：mock Gateway，指定 2 个专家，断言仅这 2 个专家的 `run_expert` 被调用
- [x] 8.4 单专家失败降级测试：mock Gateway 中某专家抛异常，断言 `overall_status` 为 `"partial"`、成功专家 data 正常、失败专家 error 被记录
- [x] 8.5 全部专家失败测试：mock Gateway 全部抛异常，断言 `overall_status` 为 `"failed"`
- [x] 8.6 Gateway Adapter dispatch 测试：mock Research Application Service，验证 `ResearchGatewayAdapter` 按 ExpertType 正确调度并传参
- [x] 8.7 全部成功测试：mock Gateway 全部成功，断言 `overall_status` 为 `"completed"`、所有专家 data 正确
- [x] 8.8 验证：Application/Domain 层无 `langgraph`/`langchain` import（静态检查）

## 9. 最终验证

- [x] 9.1 `docker compose exec app python -c "import src.main"` 正常启动
- [x] 9.2 `grep -rn "langgraph\|langchain" src/modules/coordinator/application/ src/modules/coordinator/domain/` 返回空
- [x] 9.3 全部测试通过：`docker compose exec app pytest tests/coordinator/ -v`
- [ ] 9.4 手动 API 测试：`POST /api/v1/coordinator/research` 单专家、多专家、全部专家场景正常返回
