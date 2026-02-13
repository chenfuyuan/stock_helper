## 1. Judge 模块骨架

- [x] 1.1 创建 `src/modules/judge/` 四层目录结构（application/、domain/、infrastructure/、presentation/）及所有子目录（services/、dtos/、ports/、model/、adapters/、agents/verdict/prompts/、rest/）
- [x] 1.2 创建各层 `__init__.py` 文件
- [x] 1.3 创建 `src/modules/judge/container.py` 占位文件

## 2. Judge Domain 层

- [x] 2.1 创建 `domain/model/enums.py`：定义 `ActionDirection`（BUY/SELL/HOLD）枚举
- [x] 2.2 创建 `domain/dtos/judge_input.py`：定义 `JudgeInput`（symbol/direction/confidence/bull_thesis/bear_thesis/risk_factors/key_disagreements/conflict_resolution）
- [x] 2.3 创建 `domain/dtos/verdict_result.py`：定义 `VerdictResult`（action/position_percent/confidence/entry_strategy/stop_loss/take_profit/time_horizon/risk_warnings/reasoning，不含 symbol）
- [x] 2.4 创建 `domain/ports/llm_port.py`：定义 `ILLMPort`（ABC，generate 方法签名：prompt, system_message, temperature → str）
- [x] 2.5 创建 `domain/ports/judge_verdict_agent.py`：定义 `IJudgeVerdictAgentPort`（ABC，judge 方法：JudgeInput → VerdictResult）
- [x] 2.6 创建 `domain/exceptions.py`：定义 `LLMOutputParseError` 等 Judge 领域异常（继承 AppException）

## 3. Judge Infrastructure 层 — LLM 桥接与工具

- [x] 3.1 创建 `infrastructure/adapters/llm_adapter.py`：实现 `ILLMPort`，内部委托 `llm_platform.LLMService.generate()`
- [x] 3.2 创建 `infrastructure/prompt_loader.py`：实现 load_system_prompt / load_user_prompt_template / fill_user_prompt 工具函数（复用 Debate 模式）

## 4. Judge Infrastructure 层 — Verdict Agent

- [x] 4.1 创建 `infrastructure/agents/verdict/prompts/system.md`：裁决者系统提示词（角色定义、输出格式约束、风控原则）
- [x] 4.2 创建 `infrastructure/agents/verdict/prompts/user.md`：裁决者用户提示词模板（占位符：symbol、direction、confidence、bull_thesis、bear_thesis、risk_factors、key_disagreements、conflict_resolution）
- [x] 4.3 创建 `infrastructure/agents/verdict/output_parser.py`：解析 LLM JSON 输出为 `VerdictResult` DTO，失败时抛 `LLMOutputParseError`
- [x] 4.4 创建 `infrastructure/adapters/judge_verdict_agent_adapter.py`：实现 `IJudgeVerdictAgentPort`（加载 Prompt → 填充 JudgeInput 占位符 → 调用 ILLMPort → 解析 → 返回 VerdictResult）

## 5. Judge Application 层

- [x] 5.1 创建 `application/dtos/verdict_dto.py`：定义 `VerdictDTO`（symbol/action/position_percent/confidence/entry_strategy/stop_loss/take_profit/time_horizon/risk_warnings/reasoning）
- [x] 5.2 创建 `application/services/judge_service.py`：实现 `JudgeService`——接收 JudgeInput，调用 IJudgeVerdictAgentPort.judge()，组装 VerdictDTO 返回（从 JudgeInput 注入 symbol）

## 6. Judge Presentation 层

- [x] 6.1 创建 `presentation/rest/judge_schemas.py`：定义 FastAPI 请求/响应 Schema（JudgeVerdictRequest、JudgeVerdictResponse）
- [x] 6.2 创建 `presentation/rest/judge_router.py`：实现 `POST /api/v1/judge/verdict` 路由，依赖注入 JudgeContainer，异常处理映射为 HTTP 状态码（400/500）

## 7. Judge Container 与路由注册

- [x] 7.1 完善 `container.py`：装配 LLMAdapter → JudgeVerdictAgentAdapter → JudgeService 的完整依赖链
- [x] 7.2 在 `src/api/routes.py` 中注册 Judge 路由（`api_router.include_router(judge_router)`）

## 8. Coordinator 扩展 — Domain 层

- [x] 8.1 创建 `src/modules/coordinator/domain/ports/judge_gateway.py`：定义 `IJudgeGateway`（ABC，run_verdict 方法签名：symbol + debate_outcome → dict）

## 9. Coordinator 扩展 — Infrastructure 层

- [x] 9.1 创建 `src/modules/coordinator/infrastructure/adapters/judge_gateway_adapter.py`：实现 `JudgeGatewayAdapter`——debate_outcome dict 到 JudgeInput 的字段映射（direction/confidence/bull_case.core_thesis/bear_case.core_thesis/risk_matrix→risk_factors/key_disagreements/conflict_resolution）、过滤细节字段、调用 JudgeContainer → JudgeService → 返回 dict
- [x] 9.2 扩展 `graph_state.py`：在 `ResearchGraphState` 中新增 `verdict: dict[str, Any]` 字段
- [x] 9.3 在 `graph_builder.py` 中实现 `create_judge_node()` 工厂函数：读取 debate_outcome → 为空时跳过 → 调用 IJudgeGateway → 异常时记录日志并降级（verdict 为空 dict）
- [x] 9.4 修改 `build_research_graph()` 函数签名：新增 `judge_gateway: Any = None` 参数；当 debate_gateway 和 judge_gateway 均不为 None 时构建 `debate_node → judge_node → END`；仅有 debate_gateway 时保持 `debate_node → END`；debate_gateway 为 None 时保持 `aggregator_node → END`

## 10. Coordinator 扩展 — Application 与 Presentation 层

- [x] 10.1 扩展 `LangGraphResearchOrchestrator`：构造函数接受 `judge_gateway` 参数；skip_debate 时 judge_gw 也为 None；从 final_state 提取 verdict（空 dict 转 None）写入 ResearchResult
- [x] 10.2 扩展 `ResearchResult` DTO：新增 `verdict: dict[str, Any] | None = None` 字段
- [x] 10.3 扩展 REST 响应 Schema：新增 `verdict` 字段

## 11. Coordinator Container 更新

- [x] 11.1 修改 `CoordinatorContainer`：装配 `JudgeGatewayAdapter`，将其与 `DebateGatewayAdapter` 一起传入 `LangGraphResearchOrchestrator`

## 12. 测试 — Judge 模块

- [x] 12.1 编写 output_parser 单元测试：合法 JSON 解析为 VerdictResult 成功、非法 JSON 抛 LLMOutputParseError
- [x] 12.2 编写 JudgeService 单元测试：Mock IJudgeVerdictAgentPort，验证正常流程返回完整 VerdictDTO（含正确 symbol 注入）
- [x] 12.3 编写 JudgeService 异常测试：Mock Agent Port 抛异常，验证异常向上传播
- [x] 12.4 编写 Judge REST 端点集成测试：正常请求返回 200、symbol 缺失返回 400、debate_outcome 为空返回 400

## 13. 测试 — Coordinator 扩展

- [x] 13.1 编写 JudgeGatewayAdapter 单元测试：验证 debate_outcome → JudgeInput 字段映射（bull_thesis/bear_thesis/risk_factors 提取）、细节字段过滤
- [x] 13.2 编写 judge_node 单元测试：辩论成功后正常裁决写入 verdict、debate_outcome 为空时跳过裁决、Gateway 异常时降级（verdict 为空 dict）
- [x] 13.3 编写编排图集成测试：Mock ResearchExpertGateway + DebateGateway + JudgeGateway，验证完整流水线（Research → Aggregator → Debate → Judge）返回含 verdict 的结果
- [x] 13.4 编写 skip_debate 测试：skip_debate=true 时响应 debate_outcome 和 verdict 均为 null
- [x] 13.5 编写辩论失败时裁决跳过测试：辩论异常后 verdict 为 null，debate_outcome 为 null，overall_status 不受影响
