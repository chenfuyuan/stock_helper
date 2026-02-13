## Context

研究流水线目前止步于 `aggregator_node → END`，五专家结果仅做简单汇总。Debate 模块需要插入该节点之后，消费 `ResearchResult`（五专家的 signal/confidence/reasoning），通过 LLM 驱动的结构化多空辩论，输出 `DebateOutcome`（多空论点、风险矩阵、综合结论）。

现有模式参考：
- **Research 专家**：Application Service（校验 → 数据获取 → Agent Port 调用 → 返回 dict）；Agent Adapter（加载 Prompt → `ILLMPort.generate()` → 解析 JSON）。
- **Coordinator 编排**：LangGraph StateGraph + `IResearchExpertGateway` Port/Adapter 模式；`ResearchGatewayAdapter` 通过 `ResearchContainer` 调度。
- **跨模块调用**：通过被调用方的 Application 接口 + 调用方的 Gateway Port/Adapter 桥接。

## Goals / Non-Goals

**Goals:**

- 实现 Debate Bounded Context（`src/modules/debate/`），严格遵循四层 DDD 架构。
- 提供 LLM 驱动的三阶段辩论流程：多头论证 → 空头论证（可并行） → 交叉质疑与冲突消解（串行）。
- 输出结构化的 `DebateOutcome`：多空论点摘要、风险矩阵、综合置信度与方向、冲突消解结论。
- 将 Debate 集成到 Coordinator 的 LangGraph 编排图中（`aggregator_node → debate_node → END`）。
- 提供独立的 REST 端点用于调试和独立测试。

**Non-Goals:**

- **不做持久化**：本阶段辩论结果不落库，随流水线实时返回。
- **不做多轮辩论**：初期实现单轮（Bull → Bear → Resolution），后续可扩展为多轮迭代。
- **不做 Judge 集成**：Judge 模块在后续 change 中实现，本次仅保证 Debate 输出结构对 Judge 友好。
- **不做数据采集**：Debate 不直接调用 data_engineering 或搜索，仅消费 Research 产出物。

## Decisions

### Decision 1：三阶段辩论流程（Bull → Bear → Resolution）

**选择**：将辩论拆为三次独立 LLM 调用——Bull Advocate、Bear Advocate、Resolution Judge。

**方案对比：**

| 方案 | 描述 | 优势 | 劣势 |
|------|------|------|------|
| A. 单次 LLM 调用 | 一个 Prompt 生成全部辩论内容 | 最简单、延迟低 | Prompt 过长、多空立场容易混淆、质量难控 |
| **B. 三阶段管线（选中）** | Bull/Bear 分别调用，再 Resolution 综合 | 每步聚焦、质量高、Bull/Bear 可并行 | 3 次 LLM 调用、延迟稍高 |
| C. LangGraph 子图 | Debate 内部用 LangGraph 管理状态 | 支持多轮、状态清晰 | 初期过度工程、增加复杂度 |

**理由**：方案 B 兼顾质量与复杂度。Bull 和 Bear 使用相同输入但不同 system prompt（立场对立），可并行执行以缩短延迟；Resolution 在双方论点就绪后串行执行，做交叉质疑和冲突消解。后续升级为多轮只需在 Application Service 中加循环，无需重构 Agent 层。

### Decision 2：Debate 模块内部分层与关键类

```
src/modules/debate/
├── application/
│   ├── services/
│   │   └── debate_service.py          # DebateService：编排 Bull/Bear/Resolution
│   └── dtos/
│       └── debate_outcome_dto.py      # DebateOutcomeDTO（对外暴露的结果）
├── domain/
│   ├── dtos/
│   │   ├── debate_input.py            # DebateInput（从 ResearchResult 转换而来）
│   │   ├── bull_bear_argument.py      # BullArgument / BearArgument
│   │   └── risk_matrix.py            # RiskMatrixItem
│   ├── ports/
│   │   ├── bull_advocate_agent.py     # IBullAdvocateAgentPort
│   │   ├── bear_advocate_agent.py     # IBearAdvocateAgentPort
│   │   └── resolution_agent.py        # IResolutionAgentPort
│   └── model/
│       └── enums.py                   # DebateDirection、RiskLevel 等枚举
├── infrastructure/
│   ├── adapters/
│   │   ├── llm_adapter.py            # LLMAdapter（桥接 llm_platform）
│   │   ├── bull_advocate_agent_adapter.py
│   │   ├── bear_advocate_agent_adapter.py
│   │   └── resolution_agent_adapter.py
│   └── agents/
│       ├── bull_advocate/prompts/     # system.md + user.md
│       ├── bear_advocate/prompts/
│       └── resolution/prompts/
├── presentation/
│   └── rest/
│       ├── debate_router.py           # FastAPI Router
│       └── debate_schemas.py          # 请求/响应 Schema
└── container.py                       # DebateContainer（Composition Root）
```

**理由**：复用 Research 模块的成熟模式——每个 LLM 角色（Bull/Bear/Resolution）对应一个 Agent Port + Adapter + Prompts 目录。`DebateService` 作为 Application 层入口，编排三阶段流程。

### Decision 3：输入转换——DebateInput 而非直接消费 ResearchResult

**选择**：在 Debate 的 `domain/dtos/` 中定义 `DebateInput`（从 Coordinator 传入的 `ResearchResult` 转换），而非直接 import Coordinator 的 DTO。

**理由**：
- 遵守 DDD 边界约束：Domain 层不 import 其他模块的任何类型。
- 转换在 Coordinator 的 Gateway Adapter 中完成（`DebateGatewayAdapter`），符合 tech-standards 的 "跨模块 DTO 转换在 Adapter 完成" 规范。
- `DebateInput` 只保留辩论所需的关键字段（symbol、每专家的 signal/confidence/reasoning/risk），过滤掉 raw_llm_output 等调试字段，减少 Prompt token 消耗。

### Decision 4：Coordinator 集成——新增 IDebateGateway Port

**选择**：在 Coordinator 的 `domain/ports/` 中新增 `IDebateGateway`（类似 `IResearchExpertGateway`），由 `DebateGatewayAdapter` 在 Infrastructure 层实现。

```python
# Coordinator 新增 Port
class IDebateGateway(ABC):
    async def run_debate(self, symbol: str, expert_results: dict[str, Any]) -> dict[str, Any]: ...
```

**LangGraph 图扩展**：
- 新增 `debate_node`：调用 `IDebateGateway.run_debate()`
- 修改边：`aggregator_node → debate_node → END`（替换原来的 `aggregator_node → END`）
- 扩展 `ResearchGraphState`：新增 `debate_outcome: dict[str, Any]` 字段
- `DebateGatewayAdapter` 内部通过 `DebateContainer` 获取 `DebateService` 并调用

**理由**：与 Research Gateway 模式完全一致，Coordinator 只依赖自己的 Port 抽象，不感知 Debate 的内部实现。

### Decision 5：DebateOutcome 输出结构

```python
class DebateOutcomeDTO(BaseModel):
    symbol: str
    direction: str               # "BULLISH" | "BEARISH" | "NEUTRAL"
    confidence: float            # 0.0 - 1.0，综合置信度
    bull_case: BullCaseDTO       # 多头论点摘要
    bear_case: BearCaseDTO       # 空头论点摘要
    risk_matrix: list[RiskItemDTO]  # 风险矩阵
    conflict_resolution: str     # 冲突消解结论
    key_disagreements: list[str] # 核心分歧点
```

**理由**：结构化输出便于 Judge 后续消费——Judge 需要方向/置信度做裁决，需要 risk_matrix 做风控，需要 key_disagreements 识别决策盲区。

### Decision 6：LLM 桥接复用 Research 模式

**选择**：Debate 模块定义自己的 `ILLMPort`（与 Research 的 `ILLMPort` 签名相同但独立定义），通过 `LLMAdapter` 桥接 `llm_platform.LLMService`。

**理由**：
- 每个模块维护自己的 Port，避免跨模块共享接口定义。
- 签名一致使 Adapter 实现可直接参考 Research 的 `LLMAdapter`，降低实现成本。
- 未来若 Debate 需要特殊 LLM 配置（如 temperature、model alias），可独立扩展 Port 签名。

## Risks / Trade-offs

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| **LLM 输出解析失败**：Bull/Bear/Resolution 的 JSON 输出可能不合规 | 辩论流程中断 | 每个 Agent Adapter 实现健壮的 output_parser，失败时抛 `LLMOutputParseError`；Coordinator 的 debate_node 捕获异常写入 errors，overall_status 降级为 partial |
| **延迟增加**：3 次 LLM 调用（Bull+Bear 并行 ≈ 1 次 + Resolution 1 次）增加约 10-20s | 端到端响应变慢 | Bull/Bear 并行执行（`asyncio.gather`）；Resolution 使用较低 temperature 加速收敛；后续可引入流式输出 |
| **Prompt token 超限**：五专家全量结果可能超出上下文窗口 | LLM 截断或报错 | DebateInput 转换时裁剪——只传 signal/confidence/reasoning/risk_warning，过滤 raw_output 和 indicators 原始数据 |
| **单轮辩论深度不足**：复杂标的可能需要多轮对抗才能充分暴露冲突 | 辩论质量受限 | 初期可接受——DebateService 留扩展口（循环调用 Bull→Bear→Resolution），后续通过 config 控制轮次 |
| **Coordinator 图结构变更**：修改 `aggregator_node → END` 为 `aggregator_node → debate_node → END` | 影响现有编排测试 | debate_node 默认启用；如需跳过可通过 options 参数控制（向后兼容）；更新现有 Coordinator 测试覆盖新路径 |
