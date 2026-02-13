# Spec: judge-verdict-engine

Judge 模块核心能力：接收辩论结果（`JudgeInput`，由 Coordinator Adapter 从 `DebateOutcomeDTO` 转换），通过 LLM 驱动的单次综合裁决流程，输出结构化的投资决策 `VerdictDTO`（操作方向、仓位建议、入场策略、止损止盈、持有周期、风控约束、裁决理由）。Judge 只做综合裁决与风控约束，不做研报、辩论流程或数据采集。

**测试约定**：每个 `#### Scenario:` 在变更交付时须对应至少一个自动化测试用例（单元或集成）；实现顺序可先实现再补测，以完整测试通过为需求完成标准。

---

## ADDED Requirements

### Requirement: JudgeService 编排裁决流程

`JudgeService`（Application 层，位于 `src/modules/judge/application/services/judge_service.py`）SHALL 作为 Judge 模块的唯一 Application 入口。该服务 SHALL 编排以下流程：

1. 接收 `JudgeInput` 作为入参。
2. 通过 `IJudgeVerdictAgentPort` 执行单次 LLM 裁决，获得 `VerdictResult`。
3. 将 `VerdictResult` 组装为 `VerdictDTO` 返回。

入参为 `JudgeInput`，出参为 `VerdictDTO`。

#### Scenario: 裁决正常完成

- **WHEN** 调用 `JudgeService.run(judge_input)` 且 `IJudgeVerdictAgentPort` 正常返回
- **THEN** 服务 SHALL 返回包含 action、position_percent、confidence、entry_strategy、stop_loss、take_profit、time_horizon、risk_warnings、reasoning 的 `VerdictDTO`

#### Scenario: Agent 失败时裁决中断

- **WHEN** `IJudgeVerdictAgentPort` 抛出异常
- **THEN** `JudgeService` SHALL 将异常向上传播（不吞掉），调用方可据此处理

---

### Requirement: JudgeInput — 裁决输入 DTO

`JudgeInput`（Domain 层 DTO，位于 `src/modules/judge/domain/dtos/judge_input.py`）SHALL 定义裁决所需的输入结构：

- `symbol`（str）：标的代码
- `direction`（str）：辩论综合方向，值为 `"BULLISH"` | `"BEARISH"` | `"NEUTRAL"`
- `confidence`（float）：辩论综合置信度，0.0 - 1.0
- `bull_thesis`（str）：多头核心论点
- `bear_thesis`（str）：空头核心论点
- `risk_factors`（list[str]）：风险因子摘要（从 risk_matrix 提取）
- `key_disagreements`（list[str]）：核心分歧点
- `conflict_resolution`（str）：冲突消解结论

`JudgeInput` SHALL NOT 包含以下来自 Debate 的细节字段（由调用方在转换时过滤）：
- `bull_case.supporting_arguments`：多头支持论据列表
- `bull_case.acknowledged_risks`：多头已知风险列表
- `bear_case.supporting_arguments`：空头支持论据列表
- `bear_case.acknowledged_strengths`：空头已知优势列表
- `risk_matrix` 的 probability / impact / mitigation 明细

`JudgeInput` 的字段为**归一化后的结论级字段**，由调用方（`JudgeGatewayAdapter`）从 `DebateOutcomeDTO` 的嵌套结构中提取并扁平化。

#### Scenario: JudgeInput 仅包含结论级字段

- **WHEN** 构造 `JudgeInput` 时传入辩论结果
- **THEN** `JudgeInput` SHALL 仅包含 symbol、direction、confidence、bull_thesis、bear_thesis、risk_factors、key_disagreements、conflict_resolution，SHALL NOT 包含 supporting_arguments、acknowledged_risks 等细节列表

#### Scenario: direction 值域约束

- **WHEN** 构造 `JudgeInput` 时传入 direction
- **THEN** direction SHALL 仅为 `"BULLISH"`、`"BEARISH"` 或 `"NEUTRAL"` 之一

---

### Requirement: VerdictDTO — 裁决输出 DTO

`VerdictDTO`（Application 层 DTO，位于 `src/modules/judge/application/dtos/verdict_dto.py`）SHALL 定义裁决结果结构：

- `symbol`（str）：标的代码
- `action`（str）：操作方向，值为 `"BUY"` | `"SELL"` | `"HOLD"`
- `position_percent`（float）：建议仓位比例，0.0 - 1.0
- `confidence`（float）：裁决置信度，0.0 - 1.0
- `entry_strategy`（str）：入场策略描述
- `stop_loss`（str）：止损策略描述
- `take_profit`（str）：止盈策略描述
- `time_horizon`（str）：持有周期建议
- `risk_warnings`（list[str]）：关键风控约束
- `reasoning`（str）：裁决理由摘要

所有字段 SHALL 使用基本类型或 DTO，SHALL NOT 引用 Domain 实体或值对象。

#### Scenario: 输出包含完整的裁决结构

- **WHEN** 裁决正常完成
- **THEN** `VerdictDTO` SHALL 包含 symbol、action、position_percent、confidence、entry_strategy、stop_loss、take_profit、time_horizon、risk_warnings、reasoning 全部字段

#### Scenario: action 值域约束

- **WHEN** Agent 返回操作方向
- **THEN** `action` SHALL 仅为 `"BUY"`、`"SELL"` 或 `"HOLD"` 之一

#### Scenario: position_percent 值域约束

- **WHEN** Agent 返回仓位建议
- **THEN** `position_percent` SHALL 为 0.0 至 1.0 之间的浮点数

#### Scenario: confidence 值域约束

- **WHEN** Agent 返回裁决置信度
- **THEN** `confidence` SHALL 为 0.0 至 1.0 之间的浮点数

---

### Requirement: VerdictResult — Agent 领域输出 DTO

`VerdictResult`（Domain 层 DTO，位于 `src/modules/judge/domain/dtos/verdict_result.py`）SHALL 定义 Agent 返回的原始裁决结构，字段与 `VerdictDTO` 一致（不含 `symbol`，`symbol` 由 `JudgeService` 从 `JudgeInput` 补充）：

- `action`（str）
- `position_percent`（float）
- `confidence`（float）
- `entry_strategy`（str）
- `stop_loss`（str）
- `take_profit`（str）
- `time_horizon`（str）
- `risk_warnings`（list[str]）
- `reasoning`（str）

#### Scenario: VerdictResult 不含 symbol

- **WHEN** Agent 返回 `VerdictResult`
- **THEN** `VerdictResult` SHALL NOT 包含 `symbol` 字段，`symbol` 由 `JudgeService` 从 `JudgeInput` 中获取并注入 `VerdictDTO`

---

### Requirement: IJudgeVerdictAgentPort 接口定义

Judge Domain 层（`src/modules/judge/domain/ports/judge_verdict_agent.py`）SHALL 定义 Agent Port：

`IJudgeVerdictAgentPort`：`async def judge(input: JudgeInput) -> VerdictResult`

该 Port SHALL 为 ABC 抽象类，仅定义接口签名，不包含任何 LLM 或 Infrastructure 实现。

#### Scenario: Port 接口为纯抽象

- **WHEN** 检查 `src/modules/judge/domain/ports/judge_verdict_agent.py`
- **THEN** `IJudgeVerdictAgentPort` SHALL 为继承 `abc.ABC` 的抽象类，方法标注 `@abstractmethod`

#### Scenario: Port 不依赖 Infrastructure

- **WHEN** 检查 Port 文件的 import 语句
- **THEN** SHALL NOT 包含 `infrastructure`、`langgraph`、`openai` 等 Infrastructure 层依赖

---

### Requirement: Agent Adapter 实现 — LLM Prompt 驱动

`IJudgeVerdictAgentPort` SHALL 由 Infrastructure Adapter 实现（位于 `src/modules/judge/infrastructure/adapters/judge_verdict_agent_adapter.py`）：

`JudgeVerdictAgentAdapter` 实现 `IJudgeVerdictAgentPort`。

Adapter SHALL 遵循以下流程：
1. 从 `infrastructure/agents/verdict/prompts/` 加载 `system.md` 和 `user.md`
2. 使用 `JudgeInput` 的字段填充 `user.md` 中的占位符
3. 调用 `ILLMPort.generate(prompt, system_message, temperature)` 获取 LLM 原始输出
4. 使用 output_parser 解析 JSON 为 `VerdictResult`
5. 解析失败时 SHALL 抛出 `LLMOutputParseError`

#### Scenario: Adapter 加载 Prompt 并调用 LLM

- **WHEN** `JudgeVerdictAgentAdapter.judge(input)` 被调用
- **THEN** Adapter SHALL 加载 system.md 和 user.md，填充占位符后调用 `ILLMPort.generate()`

#### Scenario: LLM 输出解析成功

- **WHEN** LLM 返回合法的 JSON 字符串
- **THEN** Adapter SHALL 将其解析为 `VerdictResult` 并返回

#### Scenario: LLM 输出解析失败

- **WHEN** LLM 返回的内容无法解析为合法 JSON 或字段不匹配
- **THEN** Adapter SHALL 抛出 `LLMOutputParseError` 异常

---

### Requirement: ILLMPort — Judge 模块的 LLM 桥接

Judge Domain 层 SHALL 定义自己的 `ILLMPort`（位于 `src/modules/judge/domain/ports/llm_port.py`），签名为：

```
async def generate(prompt: str, system_message: str | None, temperature: float) -> str
```

该 Port SHALL 由 Infrastructure 层的 `LLMAdapter`（位于 `src/modules/judge/infrastructure/adapters/llm_adapter.py`）实现，内部调用 `llm_platform` 的 `LLMService.generate()`。

Judge 的 `ILLMPort` SHALL 独立于 Debate 和 Research 的 `ILLMPort` 定义（不跨模块共享 Port）。

#### Scenario: LLMAdapter 桥接到 llm_platform

- **WHEN** Judge 的 `LLMAdapter.generate()` 被调用
- **THEN** 内部 SHALL 委托给 `llm_platform.LLMService.generate()`，并返回其结果

#### Scenario: LLM Port 定义独立于 Debate 和 Research

- **WHEN** 检查 `src/modules/judge/domain/ports/` 下的 LLM Port
- **THEN** 该 Port SHALL 定义在 Judge 模块内部，SHALL NOT import Debate 或 Research 模块的 `ILLMPort`

---

### Requirement: REST 端点 — POST /api/v1/judge/verdict

Judge 模块 SHALL 暴露 `POST /api/v1/judge/verdict` REST 端点（位于 `src/modules/judge/presentation/rest/judge_router.py`），用于独立触发裁决（调试/测试用途）。

请求体 SHALL 包含：
- `symbol`（str，必填）：标的代码
- `debate_outcome`（dict，必填）：辩论结果的 dict 表示，须包含 direction、confidence、bull_case、bear_case、risk_matrix、key_disagreements、conflict_resolution

响应体 SHALL 为 `VerdictDTO` 的 JSON 序列化。

异常处理：
- 入参校验失败 → HTTP 400
- LLM 解析失败 → HTTP 500
- 其他异常 → HTTP 500

#### Scenario: 正常调用返回裁决结果

- **WHEN** 发送 `POST /api/v1/judge/verdict` 请求体包含有效的 symbol 和 debate_outcome
- **THEN** 系统 SHALL 返回 HTTP 200，响应体为包含 action、position_percent、confidence、stop_loss、take_profit 等字段的 JSON

#### Scenario: symbol 缺失时返回 400

- **WHEN** 请求体中 symbol 为空或缺失
- **THEN** 系统 SHALL 返回 HTTP 400

#### Scenario: debate_outcome 为空时返回 400

- **WHEN** 请求体中 debate_outcome 为空 dict 或缺失
- **THEN** 系统 SHALL 返回 HTTP 400

#### Scenario: LLM 解析失败时返回 500

- **WHEN** 裁决过程中 Agent Adapter 抛出 `LLMOutputParseError`
- **THEN** 系统 SHALL 返回 HTTP 500，附带错误信息

---

### Requirement: Judge 模块四层结构与 Composition Root

Judge 模块 SHALL 位于 `src/modules/judge/`，遵循标准 DDD 四层结构：
- `application/`：`JudgeService`、`VerdictDTO` 及相关 Application DTO
- `domain/`：Agent Port 接口（`IJudgeVerdictAgentPort`）、`ILLMPort`、`JudgeInput` 及 Domain DTO、枚举、异常
- `infrastructure/`：Agent Adapter 实现、`LLMAdapter`、Prompt 文件（`agents/verdict/prompts/`）、output_parser
- `presentation/rest/`：FastAPI 路由与请求/响应 Schema

模块 SHALL 有 `container.py` 作为 Composition Root，负责装配 `LLMAdapter` → `JudgeVerdictAgentAdapter` → `JudgeService`。

#### Scenario: 模块目录结构符合四层

- **WHEN** 检查 `src/modules/judge/` 目录
- **THEN** SHALL 包含 `application/`、`domain/`、`infrastructure/`、`presentation/` 四个子目录和 `container.py`

#### Scenario: Container 装配完整依赖链

- **WHEN** 调用 `JudgeContainer` 获取 `JudgeService`
- **THEN** Container SHALL 装配 `LLMAdapter` → `JudgeVerdictAgentAdapter` → `JudgeService`，所有依赖通过构造函数注入

#### Scenario: 路由在 api/routes.py 中注册

- **WHEN** 检查 `src/api/routes.py`
- **THEN** SHALL 包含 Judge 路由的注册

---

### Requirement: Domain 枚举定义

Judge Domain 层 SHALL 在 `src/modules/judge/domain/model/enums.py` 中定义以下枚举：

- `ActionDirection`：`BUY`、`SELL`、`HOLD`

#### Scenario: 枚举涵盖所有合法操作方向

- **WHEN** 检查 `ActionDirection` 枚举
- **THEN** SHALL 包含 `BUY`、`SELL`、`HOLD` 三个成员

---

### Requirement: 可测性 — 通过 Mock Agent Port 进行测试

所有 Scenario SHALL 可通过 Mock `IJudgeVerdictAgentPort` 完成测试，无需真实 LLM 连接。

#### Scenario: 测试覆盖裁决正常流程

- **WHEN** 运行 Judge 相关测试套件
- **THEN** 存在测试用例：Mock `IJudgeVerdictAgentPort` 返回预设结果，验证 `JudgeService.run()` 返回的 `VerdictDTO` 包含正确的 action、position_percent、confidence 等字段

#### Scenario: 测试覆盖 Agent 失败场景

- **WHEN** 运行 Judge 相关测试套件
- **THEN** 存在测试用例：Mock Agent Port 抛出异常，验证 `JudgeService` 将异常向上传播

#### Scenario: 测试覆盖 output_parser

- **WHEN** 运行 Judge 相关测试套件
- **THEN** 存在测试用例：传入合法/非法 JSON 字符串，验证 output_parser 正确解析或抛出 `LLMOutputParseError`
