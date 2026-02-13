# Delta Spec: coordinator-research-orchestration

扩展 Coordinator 编排图以集成 Debate 模块：在 aggregator 节点之后新增 debate 节点，将研究汇总结果流转至 Debate 模块；新增 `IDebateGateway` Port 和对应 Adapter；扩展图状态和编排结果 DTO 以包含辩论产出。

---

## ADDED Requirements

### Requirement: IDebateGateway Port

Coordinator Domain 层 SHALL 在 `src/modules/coordinator/domain/ports/` 中新增 `IDebateGateway` 抽象接口，定义如下方法签名：

```
async def run_debate(self, symbol: str, expert_results: dict[str, Any]) -> dict[str, Any]
```

该 Port SHALL 为 ABC 抽象类，仅定义接口签名。`expert_results` 为按专家名分组的成功专家结果字典（与 `ResearchGraphState.results` 结构一致）。返回值为辩论结果的 dict 序列化形式。

#### Scenario: IDebateGateway 为纯抽象接口

- **WHEN** 检查 `src/modules/coordinator/domain/ports/debate_gateway.py`
- **THEN** `IDebateGateway` SHALL 继承 `abc.ABC`，`run_debate` 标注 `@abstractmethod`，不包含任何实现代码

#### Scenario: Port 不依赖 Debate 模块内部类型

- **WHEN** 检查 `IDebateGateway` 的 import 语句
- **THEN** SHALL NOT import Debate 模块的 Domain 实体、DTO 或 Infrastructure 类型

---

### Requirement: DebateGatewayAdapter

Coordinator Infrastructure 层 SHALL 在 `src/modules/coordinator/infrastructure/adapters/` 中新增 `DebateGatewayAdapter`，实现 `IDebateGateway`。

该 Adapter SHALL：
1. 接受 `session_factory` 参数（与 `ResearchGatewayAdapter` 一致，保证会话隔离）。
2. 在 `run_debate()` 内部创建独立 AsyncSession，通过 `DebateContainer` 获取 `DebateService`。
3. 将 `expert_results`（dict[str, Any]）转换为 Debate 模块的 `DebateInput` DTO。
4. 调用 `DebateService.run(debate_input)` 获得 `DebateOutcomeDTO`。
5. 将 `DebateOutcomeDTO` 转换为 `dict[str, Any]` 返回给 Coordinator。

**DTO 转换规则（expert_results → DebateInput）**：

转换 SHALL 在 Adapter 中完成，遵守"跨模块 DTO 转换在 Adapter 完成"的规范。由于五个专家的返回字段名各不相同，Adapter SHALL 按以下映射表将每个专家的原始结果归一化为统一的 `ExpertSummary`（signal、confidence、reasoning、risk_warning）：

| 专家 | signal 来源 | confidence 来源 | reasoning 来源 | risk_warning 来源 |
|------|------------|----------------|---------------|------------------|
| technical_analyst | `signal` | `confidence` | `summary_reasoning` | `risk_warning` |
| financial_auditor | `signal` | `confidence` | `summary_reasoning` | `risk_warning` |
| valuation_modeler | `valuation_verdict` | `confidence_score` | `reasoning_summary` | `risk_factors`（join 为字符串） |
| macro_intelligence | `macro_environment` | `confidence_score` | `macro_summary` | `key_risks`（join 为字符串） |
| catalyst_detective | `result.catalyst_assessment` | `result.confidence_score` | `result.catalyst_summary` | `result.negative_catalysts`（格式化为字符串） |

**须过滤的字段（SHALL NOT 传递给 Debate）**：

以下字段属于调试/原始数据，体积大且与辩论无关，SHALL 在转换时丢弃：
- `input` / `user_prompt`：用户提示词原文
- `output` / `raw_llm_output`：LLM 原始输出全文
- `technical_indicators` / `financial_indicators` / `valuation_indicators` / `macro_indicators`：原始指标快照数据
- `catalyst_context`：催化剂上下文原始数据
- `information_sources`：来源 URL 列表
- `dimension_analyses`：各维度详细分析数组（体积大，辩论仅需摘要级结论）
- `key_technical_levels` / `estimated_intrinsic_value_range`：技术/估值细节数据

仅成功的专家（`status == "success"`）SHALL 被包含在 `DebateInput.expert_summaries` 中；失败的专家 SHALL 被跳过。

#### Scenario: Adapter 通过 DebateContainer 调用 DebateService

- **WHEN** `DebateGatewayAdapter.run_debate()` 被调用
- **THEN** Adapter SHALL 创建独立 AsyncSession，通过 `DebateContainer` 获取 `DebateService` 并调用 `run()`

#### Scenario: technical_analyst 字段映射与过滤

- **WHEN** Adapter 接收 `expert_results` 中 `technical_analyst` 的完整结果（含 signal、confidence、summary_reasoning、risk_warning、input、output、technical_indicators、key_technical_levels）
- **THEN** 转换后的 `ExpertSummary` SHALL 仅包含 `signal="BULLISH"`、`confidence=0.78`、`reasoning="(summary_reasoning内容)"`、`risk_warning="(risk_warning内容)"`；SHALL NOT 包含 input、output、technical_indicators、key_technical_levels

#### Scenario: valuation_modeler 字段名归一化

- **WHEN** Adapter 接收 `expert_results` 中 `valuation_modeler` 的结果（字段名为 valuation_verdict、confidence_score、reasoning_summary、risk_factors）
- **THEN** 转换后的 `ExpertSummary.signal` SHALL 取自 `valuation_verdict`，`confidence` 取自 `confidence_score`，`reasoning` 取自 `reasoning_summary`，`risk_warning` 取自 `risk_factors`（列表拼接为字符串）

#### Scenario: catalyst_detective 嵌套结构展平

- **WHEN** Adapter 接收 `expert_results` 中 `catalyst_detective` 的结果（关键字段嵌套在 `result` 对象内）
- **THEN** 转换后的 `ExpertSummary.signal` SHALL 取自 `result.catalyst_assessment`，`confidence` 取自 `result.confidence_score`，`reasoning` 取自 `result.catalyst_summary`，`risk_warning` 取自 `result.negative_catalysts`（格式化为字符串）；SHALL NOT 包含 raw_llm_output、user_prompt、catalyst_context

#### Scenario: 仅成功专家被包含

- **WHEN** `expert_results` 中有 3 个成功专家和 2 个失败专家（失败专家的值为 None 或不存在于 results dict 中）
- **THEN** `DebateInput.expert_summaries` SHALL 仅包含 3 个条目，失败专家 SHALL 被跳过

#### Scenario: 返回值为 dict 序列化

- **WHEN** `DebateService.run()` 返回 `DebateOutcomeDTO`
- **THEN** Adapter SHALL 将其转为 `dict[str, Any]`（如 `.model_dump()`）后返回

---

### Requirement: debate_node 加入 LangGraph 编排图

`build_research_graph()`（位于 `src/modules/coordinator/infrastructure/orchestration/graph_builder.py`）SHALL 新增 `debate_node` 节点，该节点调用 `IDebateGateway.run_debate()`。

图的边 SHALL 修改为：
- 原来：`aggregator_node → END`
- 修改后：`aggregator_node → debate_node → END`

`debate_node` 的行为：
1. 从图状态中读取 `symbol`、`results`、`overall_status`。
2. 如果 `overall_status` 为 `"failed"`（无任何成功专家），SHALL 跳过辩论，直接返回空 `debate_outcome`。
3. 否则，调用 `IDebateGateway.run_debate(symbol, results)`。
4. 成功时将结果写入图状态的 `debate_outcome` 字段。
5. 失败时（Gateway 抛异常）记录错误日志，将 `debate_outcome` 设为 None 或空 dict，`overall_status` SHALL 不因辩论失败而改变（研究结果仍可用）。

`build_research_graph()` 的函数签名 SHALL 扩展为接受 `debate_gateway: IDebateGateway | None` 参数。当 `debate_gateway` 为 None 时，图结构 SHALL 保持原样（`aggregator_node → END`），实现向后兼容。

#### Scenario: 正常流程包含 debate_node

- **WHEN** `build_research_graph(gateway, debate_gateway)` 且 `debate_gateway` 不为 None
- **THEN** 图结构 SHALL 为 `START → route_to_experts → 专家节点（并行）→ aggregator_node → debate_node → END`

#### Scenario: debate_gateway 为 None 时保持原图结构

- **WHEN** `build_research_graph(gateway, debate_gateway=None)`
- **THEN** 图结构 SHALL 保持为 `aggregator_node → END`，与修改前行为一致

#### Scenario: 全部专家失败时跳过辩论

- **WHEN** `overall_status` 为 `"failed"`（results 为空）
- **THEN** `debate_node` SHALL 跳过辩论调用，`debate_outcome` 为空 dict

#### Scenario: 辩论异常不影响研究结果

- **WHEN** `IDebateGateway.run_debate()` 抛出异常
- **THEN** `debate_node` SHALL 捕获异常并记录错误日志，`debate_outcome` 设为空 dict，`overall_status` 保持不变（不因辩论失败变为 `"failed"`）

---

### Requirement: 扩展 ResearchGraphState

`ResearchGraphState`（位于 `src/modules/coordinator/infrastructure/orchestration/graph_state.py`）SHALL 新增字段：

- `debate_outcome: dict[str, Any]`：辩论结果，由 `debate_node` 写入

#### Scenario: 图状态包含 debate_outcome 字段

- **WHEN** 检查 `ResearchGraphState` 的 TypedDict 定义
- **THEN** SHALL 包含 `debate_outcome` 字段，类型为 `dict[str, Any]`

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

#### Scenario: 请求含完整字段时正确解析

- **WHEN** 发送请求体 `{"symbol": "000001.SZ", "experts": ["technical_analyst", "macro_intelligence"], "options": {"technical_analyst": {"analysis_date": "2026-02-13"}}}`
- **THEN** 系统 SHALL 正确解析 symbol、experts 列表和专家特有参数，调用对应的专家服务，并执行辩论阶段

#### Scenario: options 缺失时使用默认值

- **WHEN** 发送请求体不包含 `options` 字段，或 options 中不包含某专家的参数
- **THEN** 系统 SHALL 使用默认值（technical_analyst 默认 analysis_date 为当天，financial_auditor 默认 limit 为 5），正常执行

#### Scenario: 响应体包含 debate_outcome

- **WHEN** 研究编排执行完成且辩论阶段正常完成
- **THEN** 响应体 SHALL 包含 `debate_outcome` 字段，其中包含 direction、confidence、bull_case、bear_case、risk_matrix、key_disagreements、conflict_resolution

#### Scenario: skip_debate 为 true 时跳过辩论

- **WHEN** 请求体包含 `"skip_debate": true`
- **THEN** 系统 SHALL 跳过辩论阶段，响应体中 `debate_outcome` 为 `null`，其余字段不受影响

#### Scenario: 辩论失败时 debate_outcome 为 null

- **WHEN** 辩论阶段执行失败（如 LLM 解析错误）
- **THEN** 响应体 `debate_outcome` SHALL 为 `null`，`overall_status` 和 `expert_results` SHALL 不受辩论失败影响

#### Scenario: 全部成功时 overall_status 为 completed

- **WHEN** 所有选定专家均执行成功
- **THEN** `overall_status` SHALL 为 `"completed"`，所有 expert_results 中的 status 均为 `"success"`

#### Scenario: 部分成功时 overall_status 为 partial

- **WHEN** 部分选定专家执行成功、部分失败
- **THEN** `overall_status` SHALL 为 `"partial"`，成功的专家 status 为 `"success"` 含 data，失败的专家 status 为 `"failed"` 含 error

---

### Requirement: Coordinator 模块四层结构

Coordinator 模块 SHALL 位于 `src/modules/coordinator/`，遵循标准 DDD 四层结构：
- `application/`：ResearchOrchestrationService、DTO（ResearchRequest、ResearchResult）
- `domain/`：ExpertType 枚举、Port 接口（IResearchOrchestrationPort、IResearchExpertGateway、IDebateGateway）、领域异常
- `infrastructure/`：ResearchGatewayAdapter（调用 Research）、DebateGatewayAdapter（调用 Debate）、LangGraph 图构建与编排器
- `presentation/rest/`：FastAPI 路由

模块 SHALL 有 `container.py` 作为 Composition Root，负责装配全部依赖（含 DebateGatewayAdapter）。

#### Scenario: 模块目录结构符合四层

- **WHEN** 检查 `src/modules/coordinator/` 目录
- **THEN** SHALL 包含 `application/`、`domain/`、`infrastructure/`、`presentation/` 四个子目录和 `container.py`

#### Scenario: Container 装配含 DebateGatewayAdapter

- **WHEN** 调用 `CoordinatorContainer` 获取 `ResearchOrchestrationService`
- **THEN** Container SHALL 装配 `ResearchGatewayAdapter` 和 `DebateGatewayAdapter`，将 `debate_gateway` 传入 `LangGraphResearchOrchestrator`

#### Scenario: 路由在 api/routes.py 中注册

- **WHEN** 检查 `src/api/routes.py`
- **THEN** SHALL 包含 Coordinator 路由的注册
