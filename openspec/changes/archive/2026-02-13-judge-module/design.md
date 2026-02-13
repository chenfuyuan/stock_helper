## Context

研究流水线当前路径为 `Research → Aggregator → Debate → END`，Debate 输出 `DebateOutcomeDTO`（direction、confidence、bull_case、bear_case、risk_matrix、key_disagreements、conflict_resolution），但该结果仅是"辩论结论"而非"可执行操作"。Judge 模块需接入 Debate 之后，将辩论结论转化为结构化的投资操作指令。

现有模式参考：
- **Debate 模块**：Application Service（`DebateService`）编排 Agent Port 调用 → 返回 DTO；Agent Adapter 加载 Prompt → `ILLMPort.generate()` → 解析 JSON。
- **Coordinator 编排**：LangGraph StateGraph + Gateway Port/Adapter 模式；`debate_node` 通过 `IDebateGateway` 调用 Debate，异常时降级为空结果。
- **跨模块调用**：通过被调用方的 Application 接口 + 调用方的 Gateway Port/Adapter 桥接，DTO 转换在 Adapter 完成。

## Goals / Non-Goals

**Goals:**

- 实现 Judge Bounded Context（`src/modules/judge/`），严格遵循四层 DDD 架构。
- 提供 LLM 驱动的单次综合裁决流程：接收 `DebateOutcomeDTO`，输出结构化的 `VerdictDTO`。
- 将 Judge 集成到 Coordinator 的 LangGraph 编排图中（`debate_node → judge_node → END`）。
- 提供独立的 REST 端点（`POST /api/v1/judge/verdict`）用于调试和独立测试。
- 裁决输出需包含完整的操作指令：操作方向、仓位建议、入场策略、止损止盈、持有周期、风控约束、裁决理由。

**Non-Goals:**

- **不做持久化**：本阶段裁决结果不落库，随流水线实时返回。
- **不做多轮裁决**：初期实现单次裁决（一次 LLM 调用），后续可按需扩展为多维度分步裁决。
- **不做回测集成**：Judge 不直接调用 data_engineering 获取历史行情做验证；仅基于 Debate 产出裁决。
- **不做仓位管理**：Judge 仅输出「建议仓位比例」，不维护实际持仓状态或进行真实交易。
- **不做数据采集**：Judge 不直接调用 data_engineering 或 llm_platform 的搜索能力，仅消费 Debate 产出物。

## Decisions

### Decision 1：单次 LLM 裁决（而非多阶段拆分）

**选择**：Judge 使用单个 Agent（`IJudgeVerdictAgentPort`）进行一次 LLM 调用完成裁决。

**方案对比：**

| 方案 | 描述 | 优势 | 劣势 |
|------|------|------|------|
| **A. 单次裁决（选中）** | 一个 Agent，一次 LLM 调用，输入为完整 DebateOutcome | 简单、延迟低、Judge 职责聚焦 | 单次 Prompt 负载较大 |
| B. 多阶段裁决 | 拆为「信号评估 → 仓位计算 → 风控约束」三步 | 每步聚焦、可独立调优 | 3 次 LLM 调用、增加延迟和复杂度、初期过度工程 |
| C. 规则引擎 + LLM 混合 | 仓位和止损用规则计算，LLM 只做定性判断 | 仓位逻辑精确可控 | 需要额外的规则引擎基础设施，初期实现成本高 |

**理由**：与 Debate 的三阶段不同，Judge 的输入已经是高度结构化的辩论结论（方向、置信度、多空论点、风险矩阵），LLM 只需做「综合 → 决策」的单步推理。输入体积可控（DebateOutcome 约 1-2K tokens），一次调用即可输出完整裁决。后续若需精细化（如规则引擎约束仓位上限），可在 Application 层叠加后处理逻辑，无需重构 Agent。

### Decision 2：Judge 模块内部分层与关键类

```
src/modules/judge/
├── application/
│   ├── services/
│   │   └── judge_service.py              # JudgeService：编排裁决流程
│   └── dtos/
│       └── verdict_dto.py                # VerdictDTO（对外暴露的裁决结果）
├── domain/
│   ├── dtos/
│   │   ├── judge_input.py                # JudgeInput（从 DebateOutcome 转换而来）
│   │   └── verdict_result.py             # VerdictResult（Agent 返回的领域 DTO）
│   ├── ports/
│   │   ├── judge_verdict_agent.py        # IJudgeVerdictAgentPort
│   │   └── llm_port.py                   # ILLMPort（Judge 模块自有）
│   ├── model/
│   │   └── enums.py                      # ActionDirection、RiskLevel 等枚举
│   └── exceptions.py                     # 领域异常
├── infrastructure/
│   ├── adapters/
│   │   ├── judge_verdict_agent_adapter.py  # IJudgeVerdictAgentPort 实现
│   │   └── llm_adapter.py                # ILLMPort → llm_platform 桥接
│   └── agents/
│       └── verdict/prompts/              # system.md + user.md
├── presentation/
│   └── rest/
│       ├── judge_router.py               # FastAPI Router
│       └── judge_schemas.py              # 请求/响应 Schema
└── container.py                          # JudgeContainer（Composition Root）
```

**理由**：复用 Debate 模块的成熟模式——单个 Agent Port + Adapter + Prompts。相比 Debate 的三个 Agent，Judge 只需一个（`IJudgeVerdictAgentPort`），结构更简洁。`JudgeService` 作为 Application 层唯一入口，职责清晰。

### Decision 3：JudgeInput — 独立于 Debate DTO

**选择**：在 Judge 的 `domain/dtos/` 中定义 `JudgeInput`，由 Coordinator 的 `JudgeGatewayAdapter` 从 `debate_outcome`（dict）转换而来。

`JudgeInput` 字段：
- `symbol`（str）：标的代码
- `direction`（str）：辩论综合方向（BULLISH/BEARISH/NEUTRAL）
- `confidence`（float）：辩论综合置信度
- `bull_thesis`（str）：多头核心论点
- `bear_thesis`（str）：空头核心论点
- `risk_factors`（list[str]）：风险因子摘要（从 risk_matrix 提取）
- `key_disagreements`（list[str]）：核心分歧点
- `conflict_resolution`（str）：冲突消解结论

**理由**：
- 遵守 DDD 边界约束：Judge Domain 层不 import Debate 模块的任何类型。
- 转换在 Coordinator 的 `JudgeGatewayAdapter` 中完成，符合"跨模块 DTO 转换在 Adapter 完成"规范。
- `JudgeInput` 只保留裁决所需的关键结论字段，过滤 Debate 的 supporting_arguments 等细节列表，降低 Prompt token 消耗。

### Decision 4：VerdictDTO — 裁决输出结构

```python
class VerdictDTO(BaseModel):
    symbol: str
    action: str                    # "BUY" | "SELL" | "HOLD"
    position_percent: float        # 建议仓位比例，0.0 - 1.0
    confidence: float              # 裁决置信度，0.0 - 1.0
    entry_strategy: str            # 入场策略描述
    stop_loss: str                 # 止损策略
    take_profit: str               # 止盈策略
    time_horizon: str              # 持有周期建议
    risk_warnings: list[str]       # 关键风控约束
    reasoning: str                 # 裁决理由摘要
```

**理由**：覆盖投资决策的核心维度——「做什么（action）、做多少（position_percent）、怎么做（entry_strategy）、何时退（stop_loss/take_profit）、持多久（time_horizon）、风险在哪（risk_warnings）、为什么（reasoning）」。所有字段使用基本类型（str/float/list[str]），不引用 Domain 实体。

### Decision 5：Coordinator 集成 — IJudgeGateway Port

**选择**：在 Coordinator 的 `domain/ports/` 中新增 `IJudgeGateway`，由 `JudgeGatewayAdapter` 在 Infrastructure 层实现。

```python
class IJudgeGateway(ABC):
    @abstractmethod
    async def run_verdict(self, symbol: str, debate_outcome: dict[str, Any]) -> dict[str, Any]:
        """执行裁决，返回裁决结果的 dict 序列化。"""
        ...
```

**LangGraph 图扩展**：
- 新增 `judge_node`：调用 `IJudgeGateway.run_verdict()`
- 修改边：`debate_node → judge_node → END`（替换原来的 `debate_node → END`）
- 扩展 `ResearchGraphState`：新增 `verdict: dict[str, Any]` 字段
- `judge_node` 的跳过条件：`debate_outcome` 为空 dict（即辩论被跳过或失败时）不调用 Judge
- `build_research_graph()` 签名扩展：新增 `judge_gateway: Any = None` 参数

**JudgeGatewayAdapter 转换逻辑**：
- 从 `debate_outcome` dict 中提取 direction、confidence、bull_case.core_thesis、bear_case.core_thesis、risk_matrix（提取 risk 字段拼接为 list）、key_disagreements、conflict_resolution
- 构造 `JudgeInput` 传给 `JudgeService.run()`
- 将 `VerdictDTO` 通过 `model_dump()` 转为 dict 返回

**理由**：与 Debate Gateway 模式完全一致。Coordinator 只依赖自己的 Port 抽象；Judge 内部变更不影响 Coordinator。

### Decision 6：LLM 桥接独立定义

**选择**：Judge 模块定义自己的 `ILLMPort`（签名与 Debate 一致但独立定义），通过 `LLMAdapter` 桥接 `llm_platform.LLMService`。

**理由**：每个模块维护独立的 Port 定义，避免跨模块共享接口。签名一致使 Adapter 实现可直接参考 Debate 的 `LLMAdapter`。未来若 Judge 需要特殊配置（如更低 temperature 以提高确定性），可独立扩展。

### Decision 7：skip_debate 时跳过 Judge

**选择**：当 `skip_debate=true` 或辩论失败（`debate_outcome` 为空 dict）时，`judge_node` 不调用 `IJudgeGateway`，直接返回空 verdict。

**理由**：Judge 依赖 Debate 的产出作为输入。没有辩论结论就没有裁决依据，强行调用只会产生低质量的"凭空裁决"。保持流水线语义一致：跳过辩论 → 跳过裁决。

## Risks / Trade-offs

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| **LLM 输出解析失败**：VerdictResult JSON 不合规（如 action 值域偏离、position_percent 超范围） | 裁决流程中断 | output_parser 做严格 Pydantic 校验；position_percent 限制在 [0.0, 1.0]；action 限制为 BUY/SELL/HOLD；失败时抛 `LLMOutputParseError`；Coordinator 的 judge_node 捕获异常降级 |
| **Prompt 质量决定裁决质量**：Judge 的推理深度完全取决于 system.md / user.md 的设计 | 裁决可能过于笼统或脱离实际 | 初版 Prompt 参考专业投研报告格式；后续通过 A/B 测试和真实案例迭代 Prompt；Prompt 文件独立于代码，可频繁更新 |
| **单次调用限制**：复杂标的可能需要多维度分步裁决才能输出高质量指令 | 初期裁决深度有限 | 初期可接受——JudgeService 结构预留扩展口；后续可叠加「规则引擎后处理」或「多步 Agent」，无需重构核心架构 |
| **Coordinator 图结构再次变更**：`debate_node → END` 改为 `debate_node → judge_node → END` | 影响现有编排测试 | judge_gateway 参数默认为 None（向后兼容）；现有测试无需修改；新增 Judge 路径的专项测试 |
| **延迟增加**：在 Debate 的 2 次 LLM 调用基础上再加 1 次 | 端到端响应进一步变慢 | Judge 单次调用；输入体积小（DebateOutcome 结论级数据约 1K tokens）；可使用较低 temperature 加速；后续可考虑流式输出 |
