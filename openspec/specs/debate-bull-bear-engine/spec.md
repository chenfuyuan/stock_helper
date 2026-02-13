# Spec: debate-bull-bear-engine

Debate 模块核心能力：接收五专家研究结果（`DebateInput`），通过 LLM 驱动的三阶段结构化辩论流程（多头论证 → 空头论证 → 交叉质疑与冲突消解），输出 `DebateOutcomeDTO`（综合方向、置信度、多空论点摘要、风险矩阵、冲突消解结论）。Debate 只做辩论与风控，不做数据采集、研究或最终投资决策。

**三阶段流程**：Bull Advocate 与 Bear Advocate 可并行执行（相同输入、对立立场），Resolution Judge 在双方论点就绪后串行执行，进行交叉质疑与冲突消解。

**测试约定**：每个 `#### Scenario:` 在变更交付时须对应至少一个自动化测试用例（单元或集成）；实现顺序可先实现再补测，以完整测试通过为需求完成标准。

---

## ADDED Requirements

### Requirement: DebateService 编排三阶段辩论流程

`DebateService`（Application 层，位于 `src/modules/debate/application/services/debate_service.py`）SHALL 作为 Debate 模块的唯一 Application 入口。该服务 SHALL 编排以下三阶段流程：

1. **Bull Advocate**：通过 `IBullAdvocateAgentPort` 生成多头论证。
2. **Bear Advocate**：通过 `IBearAdvocateAgentPort` 生成空头论证。
3. **Resolution**：通过 `IResolutionAgentPort` 基于双方论证进行交叉质疑与冲突消解。

Bull Advocate 和 Bear Advocate SHALL 并行执行（`asyncio.gather`），Resolution SHALL 在双方论证均就绪后串行执行。

入参为 `DebateInput`，出参为 `DebateOutcomeDTO`。

#### Scenario: 三阶段正常完成

- **WHEN** 调用 `DebateService.run(debate_input)` 且三个 Agent Port 均正常返回
- **THEN** 服务 SHALL 依次完成 Bull/Bear（并行）→ Resolution（串行），返回包含方向、置信度、多空论点、风险矩阵、冲突消解结论的 `DebateOutcomeDTO`

#### Scenario: Bull 和 Bear 并行执行

- **WHEN** 调用 `DebateService.run()` 且 Bull 和 Bear Agent 各耗时约 T 秒
- **THEN** Bull 和 Bear 阶段的总耗时 SHALL 接近 T 而非 2T（并行执行）

#### Scenario: Bull Agent 失败时辩论中断

- **WHEN** `IBullAdvocateAgentPort` 抛出异常
- **THEN** `DebateService` SHALL 将异常向上传播（不吞掉），调用方可据此处理

#### Scenario: Bear Agent 失败时辩论中断

- **WHEN** `IBearAdvocateAgentPort` 抛出异常
- **THEN** `DebateService` SHALL 将异常向上传播

#### Scenario: Resolution Agent 失败时辩论中断

- **WHEN** Bull 和 Bear 均正常返回，但 `IResolutionAgentPort` 抛出异常
- **THEN** `DebateService` SHALL 将异常向上传播

---

### Requirement: DebateInput — 辩论输入 DTO

`DebateInput`（Domain 层 DTO，位于 `src/modules/debate/domain/dtos/debate_input.py`）SHALL 定义辩论所需的输入结构：

- `symbol`（str）：标的代码
- `expert_summaries`（dict[str, ExpertSummary]）：按专家名分组的摘要，key 为专家类型名（如 `"technical_analyst"`）

`ExpertSummary` SHALL 包含：
- `signal`（str）：专家信号（如 `"BULLISH"`、`"BEARISH"`）
- `confidence`（float）：置信度
- `reasoning`（str）：分析逻辑摘要
- `risk_warning`（str）：风险警示

`DebateInput` SHALL NOT 包含以下来自 Research 专家的调试/大体积字段（由调用方在转换时过滤）：
- `input` / `user_prompt`：用户提示词原文
- `output` / `raw_llm_output`：LLM 原始输出全文
- `technical_indicators` / `financial_indicators` / `valuation_indicators` / `macro_indicators`：原始指标快照
- `catalyst_context`：催化剂上下文原始数据
- `dimension_analyses`：各维度详细分析数组
- `key_technical_levels` / `estimated_intrinsic_value_range`：技术/估值细节
- `information_sources`：来源 URL 列表

`ExpertSummary` 的四个字段为**归一化后的语义字段**，由调用方（DebateGatewayAdapter）从各专家不同的原始字段名映射而来（如 valuation_modeler 的 `valuation_verdict` → `signal`，`confidence_score` → `confidence`）。

#### Scenario: ExpertSummary 仅包含四个归一化字段

- **WHEN** 构造 `DebateInput` 时传入五个专家的摘要
- **THEN** 每个 `ExpertSummary` SHALL 仅包含 signal、confidence、reasoning、risk_warning 四个字段，SHALL NOT 包含 input、output、indicators 等原始数据

#### Scenario: 部分专家缺失时仍可构造

- **WHEN** 仅有 3 个专家成功（另 2 个失败），构造 `DebateInput` 时 `expert_summaries` 仅包含 3 个 key
- **THEN** `DebateInput` SHALL 正常构造，`expert_summaries` 中仅有 3 个条目

---

### Requirement: DebateOutcomeDTO — 辩论输出 DTO

`DebateOutcomeDTO`（Application 层 DTO，位于 `src/modules/debate/application/dtos/debate_outcome_dto.py`）SHALL 定义辩论结果结构：

- `symbol`（str）：标的代码
- `direction`（str）：综合方向，值为 `"BULLISH"` | `"BEARISH"` | `"NEUTRAL"`
- `confidence`（float）：综合置信度，0.0 - 1.0
- `bull_case`（BullCaseDTO）：多头论点摘要，包含 `core_thesis`（str）、`supporting_arguments`（list）、`acknowledged_risks`（list[str]）
- `bear_case`（BearCaseDTO）：空头论点摘要，包含 `core_thesis`（str）、`supporting_arguments`（list）、`acknowledged_strengths`（list[str]）
- `risk_matrix`（list[RiskItemDTO]）：风险矩阵，每项包含 `risk`（str）、`probability`（str）、`impact`（str）、`mitigation`（str）
- `key_disagreements`（list[str]）：核心分歧点
- `conflict_resolution`（str）：冲突消解结论

所有字段 SHALL 使用基本类型或 DTO，SHALL NOT 引用 Domain 实体或值对象。

#### Scenario: 输出包含完整的辩论结构

- **WHEN** 辩论正常完成
- **THEN** `DebateOutcomeDTO` SHALL 包含 direction、confidence、bull_case、bear_case、risk_matrix、key_disagreements、conflict_resolution 全部字段

#### Scenario: direction 值域约束

- **WHEN** Resolution Agent 返回方向判断
- **THEN** `direction` SHALL 仅为 `"BULLISH"`、`"BEARISH"` 或 `"NEUTRAL"` 之一

#### Scenario: confidence 值域约束

- **WHEN** Resolution Agent 返回置信度
- **THEN** `confidence` SHALL 为 0.0 至 1.0 之间的浮点数

---

### Requirement: 三个 Agent Port 接口定义

Debate Domain 层（`src/modules/debate/domain/ports/`）SHALL 定义三个 Agent Port：

1. **`IBullAdvocateAgentPort`**：`async def advocate(input: DebateInput) -> BullArgument`
2. **`IBearAdvocateAgentPort`**：`async def advocate(input: DebateInput) -> BearArgument`
3. **`IResolutionAgentPort`**：`async def resolve(symbol: str, bull: BullArgument, bear: BearArgument) -> ResolutionResult`

这三个 Port SHALL 为 ABC 抽象类，仅定义接口签名，不包含任何 LLM 或 Infrastructure 实现。

#### Scenario: Port 接口为纯抽象

- **WHEN** 检查 `src/modules/debate/domain/ports/` 下的三个 Port 文件
- **THEN** 每个 Port SHALL 为继承 `abc.ABC` 的抽象类，方法标注 `@abstractmethod`

#### Scenario: Port 不依赖 Infrastructure

- **WHEN** 检查三个 Port 文件的 import 语句
- **THEN** SHALL NOT 包含 `infrastructure`、`langgraph`、`openai` 等 Infrastructure 层依赖

---

### Requirement: Agent Adapter 实现 — LLM Prompt 驱动

每个 Agent Port SHALL 由对应的 Infrastructure Adapter 实现（位于 `src/modules/debate/infrastructure/adapters/`）：

- `BullAdvocateAgentAdapter` 实现 `IBullAdvocateAgentPort`
- `BearAdvocateAgentAdapter` 实现 `IBearAdvocateAgentPort`
- `ResolutionAgentAdapter` 实现 `IResolutionAgentPort`

每个 Adapter SHALL 遵循以下流程：
1. 从 `infrastructure/agents/<agent_name>/prompts/` 加载 `system.md` 和 `user.md`
2. 使用 `DebateInput`（或 Bull/Bear 论证结果）填充 `user.md` 中的占位符
3. 调用 `ILLMPort.generate(prompt, system_message, temperature)` 获取 LLM 原始输出
4. 使用 output_parser 解析 JSON 为对应的 Domain DTO
5. 解析失败时 SHALL 抛出 `LLMOutputParseError`

#### Scenario: Adapter 加载 Prompt 并调用 LLM

- **WHEN** `BullAdvocateAgentAdapter.advocate(input)` 被调用
- **THEN** Adapter SHALL 加载 system.md 和 user.md，填充占位符后调用 `ILLMPort.generate()`

#### Scenario: LLM 输出解析成功

- **WHEN** LLM 返回合法的 JSON 字符串
- **THEN** Adapter SHALL 将其解析为对应的 Domain DTO（如 `BullArgument`）并返回

#### Scenario: LLM 输出解析失败

- **WHEN** LLM 返回的内容无法解析为合法 JSON 或字段不匹配
- **THEN** Adapter SHALL 抛出 `LLMOutputParseError` 异常

---

### Requirement: ILLMPort — Debate 模块的 LLM 桥接

Debate Domain 层 SHALL 定义自己的 `ILLMPort`（位于 `src/modules/debate/domain/ports/`），签名为：

```
async def generate(prompt: str, system_message: str | None, temperature: float) -> str
```

该 Port SHALL 由 Infrastructure 层的 `LLMAdapter`（位于 `src/modules/debate/infrastructure/adapters/llm_adapter.py`）实现，内部调用 `llm_platform` 的 `LLMService.generate()`。

Debate 的 `ILLMPort` SHALL 独立于 Research 的 `ILLMPort` 定义（不跨模块共享 Port）。

#### Scenario: LLMAdapter 桥接到 llm_platform

- **WHEN** Debate 的 `LLMAdapter.generate()` 被调用
- **THEN** 内部 SHALL 委托给 `llm_platform.LLMService.generate()`，并返回其结果

#### Scenario: LLM Port 定义独立于 Research

- **WHEN** 检查 `src/modules/debate/domain/ports/` 下的 LLM Port
- **THEN** 该 Port SHALL 定义在 Debate 模块内部，SHALL NOT import Research 模块的 `ILLMPort`

---

### Requirement: REST 端点 — POST /api/v1/debate/run

Debate 模块 SHALL 暴露 `POST /api/v1/debate/run` REST 端点（位于 `src/modules/debate/presentation/rest/debate_router.py`），用于独立触发辩论（调试/测试用途）。

请求体 SHALL 包含：
- `symbol`（str，必填）：标的代码
- `expert_results`（dict[str, dict]，必填）：按专家名分组的研究结果

响应体 SHALL 为 `DebateOutcomeDTO` 的 JSON 序列化。

异常处理：
- 入参校验失败 → HTTP 400
- LLM 解析失败 → HTTP 500
- 其他异常 → HTTP 500

#### Scenario: 正常调用返回辩论结果

- **WHEN** 发送 `POST /api/v1/debate/run` 请求体包含有效的 symbol 和 expert_results
- **THEN** 系统 SHALL 返回 HTTP 200，响应体为包含 direction、confidence、risk_matrix 等字段的 JSON

#### Scenario: symbol 缺失时返回 400

- **WHEN** 请求体中 symbol 为空或缺失
- **THEN** 系统 SHALL 返回 HTTP 400

#### Scenario: expert_results 为空时返回 400

- **WHEN** 请求体中 expert_results 为空 dict 或缺失
- **THEN** 系统 SHALL 返回 HTTP 400

#### Scenario: LLM 解析失败时返回 500

- **WHEN** 辩论过程中 Agent Adapter 抛出 `LLMOutputParseError`
- **THEN** 系统 SHALL 返回 HTTP 500，附带错误信息

---

### Requirement: Debate 模块四层结构与 Composition Root

Debate 模块 SHALL 位于 `src/modules/debate/`，遵循标准 DDD 四层结构：
- `application/`：`DebateService`、`DebateOutcomeDTO` 及相关 Application DTO
- `domain/`：Agent Port 接口（`IBullAdvocateAgentPort`、`IBearAdvocateAgentPort`、`IResolutionAgentPort`）、`ILLMPort`、`DebateInput` 及 Domain DTO、枚举、异常
- `infrastructure/`：Agent Adapter 实现、`LLMAdapter`、Prompt 文件（`agents/*/prompts/`）、output_parser
- `presentation/rest/`：FastAPI 路由与请求/响应 Schema

模块 SHALL 有 `container.py` 作为 Composition Root，负责装配 `LLMAdapter` → 三个 Agent Adapter → `DebateService`。

#### Scenario: 模块目录结构符合四层

- **WHEN** 检查 `src/modules/debate/` 目录
- **THEN** SHALL 包含 `application/`、`domain/`、`infrastructure/`、`presentation/` 四个子目录和 `container.py`

#### Scenario: Container 装配完整依赖链

- **WHEN** 调用 `DebateContainer` 获取 `DebateService`
- **THEN** Container SHALL 装配 `LLMAdapter` → 三个 Agent Adapter → `DebateService`，所有依赖通过构造函数注入

#### Scenario: 路由在 api/routes.py 中注册

- **WHEN** 检查 `src/api/routes.py`
- **THEN** SHALL 包含 Debate 路由的注册

---

### Requirement: Domain 枚举定义

Debate Domain 层 SHALL 在 `src/modules/debate/domain/model/enums.py` 中定义以下枚举：

- `DebateDirection`：`BULLISH`、`BEARISH`、`NEUTRAL`
- `RiskLevel`：`HIGH`、`MEDIUM`、`LOW`
- `ArgumentStrength`：`HIGH`、`MEDIUM`、`LOW`

#### Scenario: 枚举涵盖所有合法值

- **WHEN** 检查 `DebateDirection` 枚举
- **THEN** SHALL 包含 `BULLISH`、`BEARISH`、`NEUTRAL` 三个成员

#### Scenario: 风险级别枚举

- **WHEN** 检查 `RiskLevel` 枚举
- **THEN** SHALL 包含 `HIGH`、`MEDIUM`、`LOW` 三个成员

---

### Requirement: 可测性 — 通过 Mock Agent Port 进行测试

所有 Scenario SHALL 可通过 Mock 三个 Agent Port（`IBullAdvocateAgentPort`、`IBearAdvocateAgentPort`、`IResolutionAgentPort`）完成测试，无需真实 LLM 连接。

#### Scenario: 测试覆盖三阶段正常流程

- **WHEN** 运行 Debate 相关测试套件
- **THEN** 存在测试用例：Mock 三个 Agent Port 返回预设结果，验证 `DebateService.run()` 返回的 `DebateOutcomeDTO` 包含正确的 direction、confidence、risk_matrix 等字段

#### Scenario: 测试覆盖 Agent 失败场景

- **WHEN** 运行 Debate 相关测试套件
- **THEN** 存在测试用例：Mock 某个 Agent Port 抛出异常，验证 `DebateService` 将异常向上传播

#### Scenario: 测试覆盖 output_parser

- **WHEN** 运行 Debate 相关测试套件
- **THEN** 存在测试用例：传入合法/非法 JSON 字符串，验证 output_parser 正确解析或抛出 `LLMOutputParseError`
