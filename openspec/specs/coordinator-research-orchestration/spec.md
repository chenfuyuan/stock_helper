# Spec: coordinator-research-orchestration

Coordinator 模块的核心能力：通过单一 REST 端点接受研究请求（标的 + 用户指定的专家列表 + 可选参数），基于 LangGraph 有向图按需并行调用 Research 模块对应的专家 Application 服务，汇总各专家结果后统一返回。Coordinator 只做编排，不做研究、辩论或决策。

**五专家类型**：`technical_analyst`（技术分析师）、`financial_auditor`（财务审计员）、`valuation_modeler`（估值建模师）、`macro_intelligence`（宏观情报员）、`catalyst_detective`（催化剂侦探）。

**测试约定**：每个 `#### Scenario:` 在变更交付时须对应至少一个自动化测试用例（单元或集成）；实现顺序可先实现再补测，以完整测试通过为需求完成标准。

---

## ADDED Requirements

### Requirement: REST 端点 — POST /api/v1/coordinator/research

Coordinator 模块 SHALL 暴露 `POST /api/v1/coordinator/research` REST 端点，位于 `src/modules/coordinator/presentation/rest/` 下。该路由 SHALL 通过 FastAPI 依赖注入装配 `ResearchOrchestrationService` 所需的全部 Port 实现，并在路由函数中调用 `ResearchOrchestrationService.execute(request)`。路由 SHALL 在 `src/api/routes.py` 中注册。

路由 SHALL 处理以下异常并返回对应 HTTP 状态码：
- 入参校验失败（symbol 缺失、experts 为空或含非法类型）→ 400
- 全部专家执行失败 → 500
- 其他未预期异常 → 500（记录日志）

#### Scenario: HTTP 接口可正常调用

- **WHEN** 发送 `POST /api/v1/coordinator/research` 请求，请求体包含有效的 symbol 和至少一个合法的 expert
- **THEN** 系统 SHALL 通过依赖注入装配服务并返回研究编排结果，HTTP 状态码为 200

#### Scenario: symbol 缺失时返回 400

- **WHEN** 发送请求时 symbol 为空或缺失
- **THEN** 系统 SHALL 返回 HTTP 400，响应体包含可区分的错误信息

#### Scenario: experts 为空时返回 400

- **WHEN** 发送请求时 experts 列表为空数组
- **THEN** 系统 SHALL 返回 HTTP 400，响应体包含可区分的错误信息

#### Scenario: experts 含非法类型时返回 400

- **WHEN** 发送请求时 experts 列表包含不在 ExpertType 枚举中的值（如 `"unknown_expert"`）
- **THEN** 系统 SHALL 返回 HTTP 400，响应体包含可区分的错误信息

#### Scenario: 全部专家失败时返回 500

- **WHEN** 所有选定的专家均执行失败
- **THEN** 系统 SHALL 返回 HTTP 500，响应体包含错误信息

---

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

### Requirement: 用户指定专家的按需路由

Coordinator SHALL 仅调用用户在 `experts` 列表中指定的专家，SHALL NOT 调用未被指定的专家。路由逻辑 SHALL 支持任意 1 至 5 个专家的组合。

#### Scenario: 仅调用指定的专家

- **WHEN** 用户指定 `experts: ["macro_intelligence", "catalyst_detective"]`
- **THEN** 系统 SHALL 仅调用宏观情报员和催化剂侦探，SHALL NOT 调用技术分析师、财务审计员、估值建模师

#### Scenario: 指定单个专家

- **WHEN** 用户指定 `experts: ["valuation_modeler"]`
- **THEN** 系统 SHALL 仅调用估值建模师，返回仅含该专家结果的响应

#### Scenario: 指定全部五个专家

- **WHEN** 用户指定全部五个专家类型
- **THEN** 系统 SHALL 调用全部五个专家，返回包含五个专家结果的响应

---

### Requirement: 选定专家并行执行

Coordinator SHALL 并行执行所有选定的专家（通过 LangGraph `Send` API 实现动态 fan-out）。各专家的执行 SHALL 互不阻塞，不存在顺序依赖。

#### Scenario: 多专家并行执行

- **WHEN** 用户指定 3 个专家
- **THEN** 系统 SHALL 并行调用这 3 个专家，而非顺序逐个调用；总耗时 SHALL 接近最慢专家的耗时而非各专家耗时之和

#### Scenario: 单专家无需并行

- **WHEN** 用户仅指定 1 个专家
- **THEN** 系统 SHALL 直接执行该专家，结果正常返回

---

### Requirement: 单专家失败隔离与优雅降级

单个专家执行失败（异常、超时等）SHALL NOT 导致整体编排中断或其他专家的结果丢失。系统 SHALL 按以下规则处理：
- 失败的专家：记录警告日志，在响应中标记 `status: "failed"` 并附带错误信息。
- 其他成功的专家：结果正常返回。
- `overall_status` 反映整体状态：全部成功 → `"completed"`、部分成功 → `"partial"`、全部失败 → `"failed"`。

#### Scenario: 一个专家失败不影响其他专家

- **WHEN** 用户指定 3 个专家，其中 1 个执行时抛出异常，其余 2 个正常返回
- **THEN** 系统 SHALL 返回 HTTP 200，`overall_status` 为 `"partial"`，失败的专家在 `expert_results` 中标记 `status: "failed"` 并附带 error，成功的 2 个专家正常返回 data

#### Scenario: 全部专家失败

- **WHEN** 用户指定的所有专家均执行失败
- **THEN** 系统 SHALL 返回错误响应，`overall_status` 为 `"failed"`，每个专家的 error 信息均被记录

---

### Requirement: 跨模块调用通过 Domain Port

Coordinator 调用 Research 模块的专家 SHALL 通过 Coordinator Domain 层定义的 `IResearchExpertGateway` Port 进行。该 Port 的 Infrastructure Adapter（`ResearchGatewayAdapter`）内部调用 Research 模块的 Application 服务接口。Coordinator 的 Application 层和 Domain 层 SHALL NOT 直接依赖 Research 模块的任何类型（服务类、DTO、Domain 实体等）。

#### Scenario: 通过 Gateway Port 调用专家

- **WHEN** Coordinator 需要调用某个 Research 专家
- **THEN** 通过注入的 `IResearchExpertGateway` Port 调用 `run_expert(expert_type, symbol, options)`，不直接实例化或引用 Research 模块的 Application Service 类

#### Scenario: Gateway Adapter 归一化催化剂侦探返回值

- **WHEN** Gateway Adapter 调用 `CatalystDetectiveService.run()` 获得 `CatalystDetectiveAgentResult`（非 dict）
- **THEN** Adapter SHALL 将其归一化为 `dict[str, Any]`，使 Coordinator 拿到的所有专家结果类型一致

---

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

### Requirement: LangGraph 作为 Infrastructure 实现

LangGraph 的 `StateGraph`、`Send`、`TypedDict` State 等 API SHALL 仅出现在 Coordinator 的 Infrastructure 层（`infrastructure/orchestration/`）。Application 层 SHALL 通过 Domain Port（`IResearchOrchestrationPort`）委托编排执行，SHALL NOT 直接导入或使用 LangGraph 的任何类型。

#### Scenario: Application 层不依赖 LangGraph

- **WHEN** 检查 `src/modules/coordinator/application/` 下所有 Python 文件的 import 语句
- **THEN** SHALL NOT 包含任何 `langgraph` 或 `langchain` 相关的 import

#### Scenario: Domain 层不依赖 LangGraph

- **WHEN** 检查 `src/modules/coordinator/domain/` 下所有 Python 文件的 import 语句
- **THEN** SHALL NOT 包含任何 `langgraph` 或 `langchain` 相关的 import

#### Scenario: LangGraph 图构建在 Infrastructure 层

- **WHEN** 检查 LangGraph `StateGraph` 的构建与编译代码
- **THEN** 该代码 SHALL 位于 `src/modules/coordinator/infrastructure/orchestration/` 下

---

### Requirement: 编排服务入参校验

`ResearchOrchestrationService`（Application 层）SHALL 在调用编排 Port 之前校验输入：
- `symbol` 为空或 None 时，SHALL 抛出校验异常。
- `experts` 为空列表时，SHALL 抛出校验异常。
- `experts` 中含有不在 `ExpertType` 枚举中的值时，SHALL 抛出校验异常。

校验异常 SHALL 提供可区分的错误信息，便于 Presentation 层映射为 HTTP 400。

#### Scenario: symbol 缺失时校验拒绝

- **WHEN** 调用 `ResearchOrchestrationService.execute()` 时 symbol 为空字符串或 None
- **THEN** 服务 SHALL 抛出校验异常，不调用编排 Port

#### Scenario: experts 为空时校验拒绝

- **WHEN** 调用服务时 experts 为空列表
- **THEN** 服务 SHALL 抛出校验异常，不调用编排 Port

#### Scenario: experts 含非法值时校验拒绝

- **WHEN** 调用服务时 experts 列表包含 `"unknown_expert"`
- **THEN** 服务 SHALL 抛出校验异常，不调用编排 Port

---

### Requirement: ExpertType 枚举与 Domain 模型

Coordinator Domain 层 SHALL 定义 `ExpertType` 枚举，包含五个值：`TECHNICAL_ANALYST`、`FINANCIAL_AUDITOR`、`VALUATION_MODELER`、`MACRO_INTELLIGENCE`、`CATALYST_DETECTIVE`。枚举的 value SHALL 为 snake_case 字符串（如 `"technical_analyst"`），与 REST 请求体中的 experts 列表值一一对应。

Coordinator Domain 层 SHALL 定义以下 DTO：
- `ResearchRequest`：`symbol: str, experts: list[ExpertType], options: dict[str, dict]`
- `ExpertResultItem`：`expert_type: ExpertType, status: Literal["success", "failed"], data: dict | None, error: str | None`
- `ResearchResult`：`symbol: str, overall_status: Literal["completed", "partial", "failed"], expert_results: list[ExpertResultItem]`

#### Scenario: ExpertType 枚举涵盖五专家

- **WHEN** 检查 `ExpertType` 枚举定义
- **THEN** SHALL 包含 `TECHNICAL_ANALYST`、`FINANCIAL_AUDITOR`、`VALUATION_MODELER`、`MACRO_INTELLIGENCE`、`CATALYST_DETECTIVE` 五个成员，value 分别为对应的 snake_case 字符串

#### Scenario: REST 请求中的专家字符串可映射为 ExpertType

- **WHEN** REST 请求体 experts 列表包含 `"technical_analyst"`
- **THEN** 系统 SHALL 将其映射为 `ExpertType.TECHNICAL_ANALYST`

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

---

### Requirement: 可测性 — Scenario 与测试一一对应

每个上述 Scenario 在变更交付时 SHALL 对应至少一个自动化测试（单元或集成）；需求完成的验收条件包含「该需求下所有 Scenario 的测试通过」。实现时可先实现再补测，不强制测试先行。

测试 SHALL 可通过 mock `IResearchExpertGateway` 完成，无需真实 LLM 或数据库连接。

#### Scenario: 测试覆盖入参校验拒绝

- **WHEN** 运行 Coordinator 相关测试套件
- **THEN** 存在测试用例：传入缺失 symbol / 空 experts / 非法 expert 类型，断言调用被拒绝并返回可区分错误

#### Scenario: 测试覆盖按需路由

- **WHEN** 运行 Coordinator 相关测试套件
- **THEN** 存在测试用例：mock Gateway，指定 2 个专家，断言仅这 2 个专家的 `run_expert` 被调用、其余 3 个未被调用

#### Scenario: 测试覆盖单专家失败降级

- **WHEN** 运行 Coordinator 相关测试套件
- **THEN** 存在测试用例：mock Gateway 中某专家抛异常，断言 overall_status 为 `"partial"`、失败专家的 error 被记录、成功专家的 data 正常返回

#### Scenario: 测试覆盖全部专家失败

- **WHEN** 运行 Coordinator 相关测试套件
- **THEN** 存在测试用例：mock Gateway 中全部专家抛异常，断言 overall_status 为 `"failed"`

#### Scenario: 测试覆盖 Gateway Adapter dispatch

- **WHEN** 运行 Coordinator 相关测试套件
- **THEN** 存在测试用例：mock Research Application Service，验证 `ResearchGatewayAdapter` 根据 ExpertType 正确调度到对应的 Service 并传递参数
