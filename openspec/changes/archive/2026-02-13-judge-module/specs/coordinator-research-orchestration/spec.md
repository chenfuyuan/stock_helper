# Spec: coordinator-research-orchestration (Delta)

本 delta spec 描述 Judge 模块集成所需的 Coordinator 变更：新增 `IJudgeGateway` Port 和 `JudgeGatewayAdapter`，在编排图中新增 `judge_node`，扩展图状态和响应 DTO 以包含裁决结果。

---

## ADDED Requirements

### Requirement: IJudgeGateway Port

Coordinator Domain 层 SHALL 在 `src/modules/coordinator/domain/ports/` 中新增 `IJudgeGateway` 抽象接口，定义如下方法签名：

```
async def run_verdict(self, symbol: str, debate_outcome: dict[str, Any]) -> dict[str, Any]
```

该 Port SHALL 为 ABC 抽象类，仅定义接口签名。`debate_outcome` 为辩论结果的 dict 序列化（与 `ResearchGraphState.debate_outcome` 结构一致）。返回值为裁决结果的 dict 序列化形式。

#### Scenario: IJudgeGateway 为纯抽象接口

- **WHEN** 检查 `src/modules/coordinator/domain/ports/judge_gateway.py`
- **THEN** `IJudgeGateway` SHALL 继承 `abc.ABC`，`run_verdict` 标注 `@abstractmethod`，不包含任何实现代码

#### Scenario: Port 不依赖 Judge 模块内部类型

- **WHEN** 检查 `IJudgeGateway` 的 import 语句
- **THEN** SHALL NOT import Judge 模块的 Domain 实体、DTO 或 Infrastructure 类型

---

### Requirement: JudgeGatewayAdapter

Coordinator Infrastructure 层 SHALL 在 `src/modules/coordinator/infrastructure/adapters/` 中新增 `JudgeGatewayAdapter`，实现 `IJudgeGateway`。

该 Adapter SHALL：
1. 接受 `session_factory` 参数（与 `DebateGatewayAdapter` 一致，保持接口统一）。
2. 在 `run_verdict()` 内部通过 `JudgeContainer` 获取 `JudgeService`。
3. 将 `debate_outcome`（dict[str, Any]）转换为 Judge 模块的 `JudgeInput` DTO。
4. 调用 `JudgeService.run(judge_input)` 获得 `VerdictDTO`。
5. 将 `VerdictDTO` 转换为 `dict[str, Any]` 返回给 Coordinator。

**DTO 转换规则（debate_outcome → JudgeInput）**：

转换 SHALL 在 Adapter 中完成，遵守"跨模块 DTO 转换在 Adapter 完成"的规范。Adapter SHALL 按以下映射从 `debate_outcome` dict 中提取字段：

| JudgeInput 字段 | debate_outcome 来源 |
|-----------------|-------------------|
| `symbol` | 由调用方传入的 `symbol` 参数 |
| `direction` | `debate_outcome["direction"]` |
| `confidence` | `debate_outcome["confidence"]` |
| `bull_thesis` | `debate_outcome["bull_case"]["core_thesis"]` |
| `bear_thesis` | `debate_outcome["bear_case"]["core_thesis"]` |
| `risk_factors` | `debate_outcome["risk_matrix"]` 中每项的 `risk` 字段，提取为 `list[str]` |
| `key_disagreements` | `debate_outcome["key_disagreements"]` |
| `conflict_resolution` | `debate_outcome["conflict_resolution"]` |

**须过滤的字段（SHALL NOT 传递给 Judge）**：

以下 Debate 细节字段与裁决无关或体积过大，SHALL 在转换时丢弃：
- `bull_case.supporting_arguments`：多头支持论据列表
- `bull_case.acknowledged_risks`：多头已知风险列表
- `bear_case.supporting_arguments`：空头支持论据列表
- `bear_case.acknowledged_strengths`：空头已知优势列表
- `risk_matrix` 中每项的 `probability`、`impact`、`mitigation` 明细

#### Scenario: Adapter 通过 JudgeContainer 调用 JudgeService

- **WHEN** `JudgeGatewayAdapter.run_verdict()` 被调用
- **THEN** Adapter SHALL 通过 `JudgeContainer` 获取 `JudgeService` 并调用 `run()`

#### Scenario: bull_thesis 和 bear_thesis 提取

- **WHEN** Adapter 接收 `debate_outcome` 中包含 `bull_case.core_thesis="估值低于内在价值"` 和 `bear_case.core_thesis="行业景气度下行"`
- **THEN** 转换后的 `JudgeInput.bull_thesis` SHALL 为 `"估值低于内在价值"`，`bear_thesis` SHALL 为 `"行业景气度下行"`

#### Scenario: risk_factors 从 risk_matrix 提取

- **WHEN** Adapter 接收 `debate_outcome` 中 `risk_matrix` 包含 3 项，每项有 `risk`、`probability`、`impact`、`mitigation`
- **THEN** 转换后的 `JudgeInput.risk_factors` SHALL 仅包含 3 个 `risk` 字符串，SHALL NOT 包含 probability、impact、mitigation

#### Scenario: 返回值为 dict 序列化

- **WHEN** `JudgeService.run()` 返回 `VerdictDTO`
- **THEN** Adapter SHALL 将其转为 `dict[str, Any]`（如 `.model_dump()`）后返回

---

### Requirement: judge_node 加入 LangGraph 编排图

`build_research_graph()`（位于 `src/modules/coordinator/infrastructure/orchestration/graph_builder.py`）SHALL 新增 `judge_node` 节点，该节点调用 `IJudgeGateway.run_verdict()`。

`judge_node` 的行为：
1. 从图状态中读取 `symbol`、`debate_outcome`。
2. 如果 `debate_outcome` 为空 dict 或 None（辩论被跳过或失败），SHALL 跳过裁决，直接返回空 `verdict`。
3. 否则，调用 `IJudgeGateway.run_verdict(symbol, debate_outcome)`。
4. 成功时将结果写入图状态的 `verdict` 字段。
5. 失败时（Gateway 抛异常）记录错误日志，将 `verdict` 设为空 dict，`overall_status` SHALL 不因裁决失败而改变（研究和辩论结果仍可用）。

#### Scenario: 辩论成功后执行裁决

- **WHEN** `debate_outcome` 为非空 dict（辩论正常完成）
- **THEN** `judge_node` SHALL 调用 `IJudgeGateway.run_verdict(symbol, debate_outcome)` 并将结果写入 `verdict`

#### Scenario: 辩论为空时跳过裁决

- **WHEN** `debate_outcome` 为空 dict 或 None（辩论被跳过或失败）
- **THEN** `judge_node` SHALL 跳过裁决调用，`verdict` 为空 dict

#### Scenario: 裁决异常不影响研究和辩论结果

- **WHEN** `IJudgeGateway.run_verdict()` 抛出异常
- **THEN** `judge_node` SHALL 捕获异常并记录错误日志，`verdict` 设为空 dict，`overall_status` 和 `debate_outcome` 保持不变

---

## MODIFIED Requirements

### Requirement: 请求体与响应体契约

REST 端点的请求体 SHALL 为 JSON，包含以下字段：
- `symbol`（str，必填）：股票代码
- `experts`（list[str]，必填）：需要执行的专家类型列表，值为 ExpertType 枚举的 value（snake_case），至少 1 个
- `options`（dict[str, dict]，可选）：按专家名提供的专家特有参数。`technical_analyst` 可接受 `analysis_date`（str，ISO 格式日期，默认当天）；`financial_auditor` 可接受 `limit`（int，默认 5）；其他三专家无额外参数。
- `skip_debate`（bool，可选，默认 `false`）：若为 `true`，编排图 SHALL 跳过辩论阶段，行为与修改前一致。

响应体 SHALL 为 JSON，包含以下字段：
- `symbol`（str）：请求的股票代码
- `overall_status`（str）：`"completed"`（全部成功）、`"partial"`（部分成功部分失败）、`"failed"`（全部失败）
- `expert_results`（dict[str, object]）：按专家名分组的结果，每个专家的值包含 `status`（`"success"` 或 `"failed"`）、成功时包含 `data`（该专家的原始分析结果 dict）、失败时包含 `error`（错误信息字符串）
- `debate_outcome`（object | null）：辩论结果。包含 direction、confidence、bull_case、bear_case、risk_matrix、key_disagreements、conflict_resolution。当 `skip_debate=true` 或辩论失败时为 `null`。
- `verdict`（object | null）：裁决结果。包含 action、position_percent、confidence、entry_strategy、stop_loss、take_profit、time_horizon、risk_warnings、reasoning。当 `skip_debate=true`、辩论失败或裁决失败时为 `null`。

#### Scenario: 请求含完整字段时正确解析

- **WHEN** 发送请求体 `{"symbol": "000001.SZ", "experts": ["technical_analyst", "macro_intelligence"], "options": {"technical_analyst": {"analysis_date": "2026-02-13"}}}`
- **THEN** 系统 SHALL 正确解析 symbol、experts 列表和专家特有参数，调用对应的专家服务，并执行辩论和裁决阶段

#### Scenario: options 缺失时使用默认值

- **WHEN** 发送请求体不包含 `options` 字段，或 options 中不包含某专家的参数
- **THEN** 系统 SHALL 使用默认值（technical_analyst 默认 analysis_date 为当天，financial_auditor 默认 limit 为 5），正常执行

#### Scenario: 响应体包含 debate_outcome

- **WHEN** 研究编排执行完成且辩论阶段正常完成
- **THEN** 响应体 SHALL 包含 `debate_outcome` 字段，其中包含 direction、confidence、bull_case、bear_case、risk_matrix、key_disagreements、conflict_resolution

#### Scenario: 响应体包含 verdict

- **WHEN** 研究编排执行完成且辩论和裁决阶段均正常完成
- **THEN** 响应体 SHALL 包含 `verdict` 字段，其中包含 action、position_percent、confidence、entry_strategy、stop_loss、take_profit、time_horizon、risk_warnings、reasoning

#### Scenario: skip_debate 为 true 时跳过辩论和裁决

- **WHEN** 请求体包含 `"skip_debate": true`
- **THEN** 系统 SHALL 跳过辩论和裁决阶段，响应体中 `debate_outcome` 和 `verdict` 均为 `null`，其余字段不受影响

#### Scenario: 辩论失败时 debate_outcome 和 verdict 均为 null

- **WHEN** 辩论阶段执行失败（如 LLM 解析错误）
- **THEN** 响应体 `debate_outcome` 和 `verdict` SHALL 均为 `null`，`overall_status` 和 `expert_results` SHALL 不受辩论失败影响

#### Scenario: 辩论成功但裁决失败时 verdict 为 null

- **WHEN** 辩论阶段正常完成但裁决阶段执行失败
- **THEN** 响应体 `debate_outcome` SHALL 正常返回，`verdict` SHALL 为 `null`，`overall_status` 和 `expert_results` SHALL 不受裁决失败影响

#### Scenario: 全部成功时 overall_status 为 completed

- **WHEN** 所有选定专家均执行成功
- **THEN** `overall_status` SHALL 为 `"completed"`，所有 expert_results 中的 status 均为 `"success"`

#### Scenario: 部分成功时 overall_status 为 partial

- **WHEN** 部分选定专家执行成功、部分失败
- **THEN** `overall_status` SHALL 为 `"partial"`，成功的专家 status 为 `"success"` 含 data，失败的专家 status 为 `"failed"` 含 error

---

### Requirement: debate_node 加入 LangGraph 编排图

`build_research_graph()`（位于 `src/modules/coordinator/infrastructure/orchestration/graph_builder.py`）SHALL 包含 `debate_node` 节点，该节点调用 `IDebateGateway.run_debate()`。

`build_research_graph()` 的函数签名 SHALL 为：

```
def build_research_graph(
    gateway: IResearchExpertGateway,
    debate_gateway: Any = None,
    judge_gateway: Any = None,
) -> Any
```

图的边 SHALL 根据传入的 gateway 参数动态构建：
- `debate_gateway` 不为 None 且 `judge_gateway` 不为 None：`aggregator_node → debate_node → judge_node → END`
- `debate_gateway` 不为 None 且 `judge_gateway` 为 None：`aggregator_node → debate_node → END`
- `debate_gateway` 为 None：`aggregator_node → END`（无论 `judge_gateway` 是否存在，跳过辩论时也跳过裁决）

`debate_node` 的行为不变：
1. 从图状态中读取 `symbol`、`results`、`overall_status`。
2. 如果 `overall_status` 为 `"failed"`（无任何成功专家），SHALL 跳过辩论，直接返回空 `debate_outcome`。
3. 否则，调用 `IDebateGateway.run_debate(symbol, results)`。
4. 成功时将结果写入图状态的 `debate_outcome` 字段。
5. 失败时（Gateway 抛异常）记录错误日志，将 `debate_outcome` 设为空 dict，`overall_status` SHALL 不因辩论失败而改变。

#### Scenario: 正常流程包含 debate_node 和 judge_node

- **WHEN** `build_research_graph(gateway, debate_gateway, judge_gateway)` 且 `debate_gateway` 和 `judge_gateway` 均不为 None
- **THEN** 图结构 SHALL 为 `START → route_to_experts → 专家节点（并行）→ aggregator_node → debate_node → judge_node → END`

#### Scenario: 仅有 debate_gateway 时保持 debate → END

- **WHEN** `build_research_graph(gateway, debate_gateway, judge_gateway=None)`
- **THEN** 图结构 SHALL 为 `aggregator_node → debate_node → END`，与 Judge 模块引入前行为一致

#### Scenario: debate_gateway 为 None 时保持原图结构

- **WHEN** `build_research_graph(gateway, debate_gateway=None)`
- **THEN** 图结构 SHALL 保持为 `aggregator_node → END`，无论 `judge_gateway` 是否存在

#### Scenario: 全部专家失败时跳过辩论

- **WHEN** `overall_status` 为 `"failed"`（results 为空）
- **THEN** `debate_node` SHALL 跳过辩论调用，`debate_outcome` 为空 dict

#### Scenario: 辩论异常不影响研究结果

- **WHEN** `IDebateGateway.run_debate()` 抛出异常
- **THEN** `debate_node` SHALL 捕获异常并记录错误日志，`debate_outcome` 设为空 dict，`overall_status` 保持不变（不因辩论失败变为 `"failed"`）

---

### Requirement: 扩展 ResearchGraphState

`ResearchGraphState`（位于 `src/modules/coordinator/infrastructure/orchestration/graph_state.py`）SHALL 包含以下字段：

- `symbol`（str）：标的代码
- `selected_experts`（list[str]）：选中的专家列表
- `options`（dict[str, dict[str, Any]]）：专家特有参数
- `results`（Annotated[dict[str, Any], merge_dicts]）：专家结果
- `errors`（Annotated[dict[str, str], merge_dicts]）：专家错误
- `overall_status`（Literal["completed", "partial", "failed"]）：整体状态
- `debate_outcome`（dict[str, Any]）：辩论结果，由 `debate_node` 写入
- `verdict`（dict[str, Any]）：裁决结果，由 `judge_node` 写入

#### Scenario: 图状态包含 verdict 字段

- **WHEN** 检查 `ResearchGraphState` 的 TypedDict 定义
- **THEN** SHALL 包含 `verdict` 字段，类型为 `dict[str, Any]`

#### Scenario: 图状态包含 debate_outcome 字段

- **WHEN** 检查 `ResearchGraphState` 的 TypedDict 定义
- **THEN** SHALL 包含 `debate_outcome` 字段，类型为 `dict[str, Any]`

---

### Requirement: Coordinator 模块四层结构

Coordinator 模块 SHALL 位于 `src/modules/coordinator/`，遵循标准 DDD 四层结构：
- `application/`：ResearchOrchestrationService、DTO（ResearchRequest、ResearchResult）
- `domain/`：ExpertType 枚举、Port 接口（IResearchOrchestrationPort、IResearchExpertGateway、IDebateGateway、IJudgeGateway）、领域异常
- `infrastructure/`：ResearchGatewayAdapter（调用 Research）、DebateGatewayAdapter（调用 Debate）、JudgeGatewayAdapter（调用 Judge）、LangGraph 图构建与编排器
- `presentation/rest/`：FastAPI 路由

模块 SHALL 有 `container.py` 作为 Composition Root，负责装配全部依赖（含 DebateGatewayAdapter 和 JudgeGatewayAdapter）。

#### Scenario: 模块目录结构符合四层

- **WHEN** 检查 `src/modules/coordinator/` 目录
- **THEN** SHALL 包含 `application/`、`domain/`、`infrastructure/`、`presentation/` 四个子目录和 `container.py`

#### Scenario: Container 装配含 JudgeGatewayAdapter

- **WHEN** 调用 `CoordinatorContainer` 获取 `ResearchOrchestrationService`
- **THEN** Container SHALL 装配 `ResearchGatewayAdapter`、`DebateGatewayAdapter` 和 `JudgeGatewayAdapter`，将 `debate_gateway` 和 `judge_gateway` 传入 `LangGraphResearchOrchestrator`

#### Scenario: 路由在 api/routes.py 中注册

- **WHEN** 检查 `src/api/routes.py`
- **THEN** SHALL 包含 Coordinator 路由的注册

---

### Requirement: ResearchResult DTO 包含 verdict

`ResearchResult`（位于 `src/modules/coordinator/domain/dtos/research_dtos.py`）SHALL 包含以下字段：

- `symbol`（str）
- `overall_status`（Literal["completed", "partial", "failed"]）
- `expert_results`（list[ExpertResultItem]）
- `debate_outcome`（dict[str, Any] | None）：辩论结果，skip_debate 或失败时为 None
- `verdict`（dict[str, Any] | None）：裁决结果，辩论未执行或裁决失败时为 None

#### Scenario: ResearchResult 包含 verdict 字段

- **WHEN** 检查 `ResearchResult` 的定义
- **THEN** SHALL 包含 `verdict` 字段，类型为 `dict[str, Any] | None`，默认为 `None`

#### Scenario: 裁决成功时 verdict 不为 None

- **WHEN** 编排完成且裁决阶段正常返回
- **THEN** `ResearchResult.verdict` SHALL 包含裁决结果 dict

#### Scenario: 裁决失败时 verdict 为 None

- **WHEN** 裁决阶段执行失败或被跳过
- **THEN** `ResearchResult.verdict` SHALL 为 `None`

---

### Requirement: LangGraphResearchOrchestrator 支持 judge_gateway

`LangGraphResearchOrchestrator`（位于 `src/modules/coordinator/infrastructure/orchestration/langgraph_orchestrator.py`）SHALL 支持 `judge_gateway` 参数。

构造函数 SHALL 接受：
- `gateway: IResearchExpertGateway`
- `debate_gateway: Any = None`
- `judge_gateway: Any = None`

`run()` 方法中：
- 当 `request.skip_debate` 为 True 时，`debate_gw` 和 `judge_gw` 均为 None（跳过辩论则跳过裁决）。
- 否则使用构造时注入的 `debate_gateway` 和 `judge_gateway`。
- 从 `final_state` 中读取 `verdict` 字段，空 dict 转为 None，写入 `ResearchResult.verdict`。

#### Scenario: skip_debate 时跳过辩论和裁决

- **WHEN** `request.skip_debate` 为 True
- **THEN** `build_research_graph()` SHALL 接收 `debate_gateway=None` 和 `judge_gateway=None`，辩论和裁决均不执行

#### Scenario: 正常流程传入 judge_gateway

- **WHEN** `request.skip_debate` 为 False 且 `judge_gateway` 不为 None
- **THEN** `build_research_graph()` SHALL 接收 `judge_gateway`，图中包含 `judge_node`

#### Scenario: verdict 空 dict 转为 None

- **WHEN** `final_state["verdict"]` 为空 dict
- **THEN** `ResearchResult.verdict` SHALL 为 `None`
