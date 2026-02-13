## 1. Debate 模块骨架

- [x] 1.1 创建 `src/modules/debate/` 四层目录结构（application/、domain/、infrastructure/、presentation/）及所有子目录（services/、dtos/、ports/、model/、adapters/、agents/、rest/）
- [x] 1.2 创建各层 `__init__.py` 文件
- [x] 1.3 创建 `src/modules/debate/container.py` 占位文件

## 2. Debate Domain 层

- [x] 2.1 创建 `domain/model/enums.py`：定义 `DebateDirection`（BULLISH/BEARISH/NEUTRAL）、`RiskLevel`（HIGH/MEDIUM/LOW）、`ArgumentStrength`（HIGH/MEDIUM/LOW）枚举
- [x] 2.2 创建 `domain/dtos/debate_input.py`：定义 `ExpertSummary`（signal/confidence/reasoning/risk_warning）和 `DebateInput`（symbol + expert_summaries dict）
- [x] 2.3 创建 `domain/dtos/bull_bear_argument.py`：定义 `BullArgument`（direction/confidence/core_thesis/supporting_arguments/acknowledged_risks/price_catalysts）和 `BearArgument`（direction/confidence/core_thesis/supporting_arguments/acknowledged_strengths/risk_triggers）
- [x] 2.4 创建 `domain/dtos/resolution_result.py`：定义 `ResolutionResult`（direction/confidence/bull_case_summary/bear_case_summary/risk_matrix/key_disagreements/conflict_resolution）
- [x] 2.5 创建 `domain/dtos/risk_matrix.py`：定义 `RiskItemDTO`（risk/probability/impact/mitigation）
- [x] 2.6 创建 `domain/ports/llm.py`：定义 `ILLMPort`（ABC，generate 方法签名）
- [x] 2.7 创建 `domain/ports/bull_advocate_agent.py`：定义 `IBullAdvocateAgentPort`（ABC，advocate 方法）
- [x] 2.8 创建 `domain/ports/bear_advocate_agent.py`：定义 `IBearAdvocateAgentPort`（ABC，advocate 方法）
- [x] 2.9 创建 `domain/ports/resolution_agent.py`：定义 `IResolutionAgentPort`（ABC，resolve 方法）
- [x] 2.10 创建 `domain/exceptions.py`：定义 `LLMOutputParseError` 等 Debate 领域异常（继承 AppException）

## 3. Debate Infrastructure 层 — LLM 桥接与工具

- [x] 3.1 创建 `infrastructure/adapters/llm_adapter.py`：实现 `ILLMPort`，内部委托 `llm_platform.LLMService.generate()`
- [x] 3.2 创建 `infrastructure/prompt_loader.py`：实现 load_system_prompt / load_user_prompt_template / fill_user_prompt 工具函数（复用 Research 模式）

## 4. Debate Infrastructure 层 — Bull Advocate Agent

- [x] 4.1 创建 `infrastructure/agents/bull_advocate/output_parser.py`：解析 LLM JSON 输出为 `BullArgument` DTO，失败时抛 `LLMOutputParseError`
- [x] 4.2 创建 `infrastructure/adapters/bull_advocate_agent_adapter.py`：实现 `IBullAdvocateAgentPort`（加载 Prompt → 填充 DebateInput 占位符 → 调用 ILLMPort → 解析 → 返回 BullArgument）

## 5. Debate Infrastructure 层 — Bear Advocate Agent

- [x] 5.1 创建 `infrastructure/agents/bear_advocate/output_parser.py`：解析 LLM JSON 输出为 `BearArgument` DTO
- [x] 5.2 创建 `infrastructure/adapters/bear_advocate_agent_adapter.py`：实现 `IBearAdvocateAgentPort`

## 6. Debate Infrastructure 层 — Resolution Agent

- [x] 6.1 创建 `infrastructure/agents/resolution/output_parser.py`：解析 LLM JSON 输出为 `ResolutionResult` DTO
- [x] 6.2 创建 `infrastructure/adapters/resolution_agent_adapter.py`：实现 `IResolutionAgentPort`（加载 Prompt → 填充 Bull/Bear 论证占位符 → 调用 ILLMPort → 解析 → 返回 ResolutionResult）

## 7. Debate Application 层

- [x] 7.1 创建 `application/dtos/debate_outcome_dto.py`：定义 `BullCaseDTO`、`BearCaseDTO`、`DebateOutcomeDTO`（对外暴露的结果 DTO）
- [x] 7.2 创建 `application/services/debate_service.py`：实现 `DebateService`——入参校验、Bull/Bear 并行执行（asyncio.gather）、Resolution 串行执行、组装 DebateOutcomeDTO 返回

## 8. Debate Presentation 层

- [x] 8.1 创建 `presentation/rest/debate_schemas.py`：定义 FastAPI 请求/响应 Schema（DebateRunRequest、DebateRunResponse）
- [x] 8.2 创建 `presentation/rest/debate_router.py`：实现 `POST /api/v1/debate/run` 路由，依赖注入 DebateContainer，异常处理映射为 HTTP 状态码

## 9. Debate Container 与路由注册

- [x] 9.1 完善 `container.py`：装配 LLMAdapter → 三个 Agent Adapter → DebateService 的完整依赖链
- [x] 9.2 在 `src/api/routes.py` 中注册 Debate 路由（`api_router.include_router(debate_router)`）

## 10. Coordinator 扩展 — Domain 层

- [x] 10.1 创建 `src/modules/coordinator/domain/ports/debate_gateway.py`：定义 `IDebateGateway`（ABC，run_debate 方法签名）

## 11. Coordinator 扩展 — Infrastructure 层

- [x] 11.1 创建 `src/modules/coordinator/infrastructure/adapters/debate_gateway_adapter.py`：实现 `DebateGatewayAdapter`——会话隔离、per-expert 字段映射（5 专家归一化为 ExpertSummary）、过滤调试字段（input/output/indicators 等）、调用 DebateContainer → DebateService → 返回 dict
- [x] 11.2 扩展 `graph_state.py`：在 `ResearchGraphState` 中新增 `debate_outcome: dict[str, Any]` 字段
- [x] 11.3 在 `graph_builder.py` 中实现 `create_debate_node()` 工厂函数：读取 results/overall_status → 全部失败时跳过 → 调用 IDebateGateway → 异常时记录日志并降级
- [x] 11.4 修改 `build_research_graph()` 函数签名：新增 `debate_gateway: IDebateGateway | None` 参数；当不为 None 时新增 debate_node 并修改边为 `aggregator_node → debate_node → END`；为 None 时保持原图结构

## 12. Coordinator 扩展 — Application 与 Presentation 层

- [x] 12.1 扩展 `LangGraphResearchOrchestrator`：构造函数接受 `debate_gateway` 参数，传递给 `build_research_graph()`；`run()` 方法从 final_state 中提取 `debate_outcome` 并填入结果
- [x] 12.2 扩展 `ResearchResult` DTO：新增 `debate_outcome: dict[str, Any] | None` 字段
- [x] 12.3 扩展 REST 请求 Schema：新增 `skip_debate: bool = False` 字段
- [x] 12.4 扩展 REST 响应 Schema：新增 `debate_outcome` 字段
- [x] 12.5 修改路由/编排服务：将 `skip_debate` 参数透传至编排器（控制是否传入 debate_gateway）

## 13. Coordinator Container 更新

- [x] 13.1 修改 `CoordinatorContainer`：装配 `DebateGatewayAdapter`（使用 AsyncSessionLocal），将其传入 `LangGraphResearchOrchestrator`

## 14. 测试 — Debate 模块

- [x] 14.1 编写 output_parser 单元测试：合法 JSON 解析成功、非法 JSON 抛 LLMOutputParseError（Bull/Bear/Resolution 各一组）
- [x] 14.2 编写 DebateService 单元测试：Mock 三个 Agent Port，验证三阶段正常流程返回完整 DebateOutcomeDTO
- [x] 14.3 编写 DebateService 异常测试：Mock 某个 Agent Port 抛异常，验证异常向上传播
- [x] 14.4 编写 Debate REST 端点集成测试：正常请求返回 200、symbol 缺失返回 400、expert_results 为空返回 400

## 15. 测试 — Coordinator 扩展

- [x] 15.1 编写 DebateGatewayAdapter 单元测试：验证 per-expert 字段映射（5 专家归一化）、调试字段过滤、仅成功专家被包含
- [x] 15.2 编写 debate_node 单元测试：正常辩论写入 debate_outcome、全部专家失败时跳过辩论、Gateway 异常时降级（debate_outcome 为空 dict）
- [x] 15.3 编写编排图集成测试：Mock ResearchExpertGateway + DebateGateway，验证完整流水线（Research → Aggregator → Debate）返回含 debate_outcome 的结果
- [x] 15.4 编写 skip_debate 测试：请求体 skip_debate=true 时响应 debate_outcome 为 null
