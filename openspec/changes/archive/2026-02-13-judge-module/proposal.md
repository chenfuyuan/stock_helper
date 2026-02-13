## Why

研究流水线 `Coordinator → Research → Debate → Judge` 中，Research（五专家分析）和 Debate（多空对抗辩论）已全部就绪，但流水线止步于辩论产出——`DebateOutcomeDTO` 包含了方向判断、多空论点、风险矩阵和冲突消解结论，却没有最终裁决环节将这些结构化信息转化为**可执行的投资操作指令**。没有 Judge 模块，辩论结果只是"分析参考"而非"决策依据"，用户仍需自行判断仓位大小、止损止盈点位和具体操作时机。Judge 是流水线贯通的最后一块拼图，补齐后系统才能实现「采集 → 辩论 → 决策」的完整闭环。

## What Changes

- **新增 Judge Bounded Context**（`src/modules/judge/`）：实现最终裁决引擎，消费 Debate 的 `DebateOutcomeDTO`，通过 LLM 驱动的综合裁决流程，输出结构化的投资决策——包括操作方向（买入/卖出/观望）、建议仓位比例、入场策略、止损止盈点位、持有周期建议和关键风控约束。
- **新增 Judge Application 接口**：对外暴露裁决用例（`JudgeService`），供 Coordinator 通过 Port/Adapter 调用。
- **扩展 Coordinator 编排图**：在 LangGraph 的 `debate_node` 之后接入 `judge_node`，将辩论结果流转至 Judge 模块，使流水线完整为 `Research → Aggregator → Debate → Judge → END`。
- **新增 Judge REST 端点**：提供独立的裁决触发接口（`POST /api/v1/judge/verdict`），便于调试和独立测试。

## Capabilities

### New Capabilities

- `judge-verdict-engine`：Judge 模块核心能力——接收辩论结果（`DebateOutcomeDTO`），通过 LLM 驱动的综合裁决流程，输出结构化的投资决策 `VerdictDTO`（操作方向、仓位建议、入场策略、止损止盈、持有周期、风控约束、裁决理由摘要）。Judge 只做综合裁决与风控约束，不做研报、辩论或数据采集。

### Modified Capabilities

- `coordinator-research-orchestration`：扩展 Coordinator 编排图，在 `debate_node` 之后新增 `judge_node`，将辩论结果流转至 Judge 模块；新增 `IJudgeGateway` Port 和对应 Adapter；更新 `ResearchGraphState` 和响应 DTO 以包含裁决结果；`skip_debate` 为 true 或辩论失败时跳过 Judge。

## Impact

- **新增代码**：`src/modules/judge/`（domain / application / infrastructure / presentation 四层），预计新增 10-15 个文件。
- **修改代码**：`src/modules/coordinator/`——graph_builder 新增 `judge_node` 与边、新增 `IJudgeGateway` Port、新增 `JudgeGatewayAdapter`、扩展 `ResearchGraphState`（新增 `verdict` 字段）和响应 DTO。
- **依赖**：Judge 模块依赖 `llm_platform` 的 LLM 能力（通过自身 `ILLMPort` + `LLMAdapter` 桥接）；不直接依赖 `data_engineering` 或 `research`。
- **API**：新增 `POST /api/v1/judge/verdict` REST 端点；现有 `POST /api/v1/coordinator/research` 的响应结构将扩展以包含 `verdict` 字段。
- **数据库**：本阶段暂不涉及持久化（裁决结果随流水线返回，不落库），后续可按需扩展。
- **测试**：需新增 Judge 模块单元测试（Mock LLM Port）；Coordinator 编排测试需覆盖含 Judge 节点的完整流水线。
