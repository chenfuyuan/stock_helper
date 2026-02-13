## Why

研究流水线 `Coordinator → Research → Debate → Judge` 中，Research 模块（五专家）已全部就绪，但五位专家的分析结果目前只是简单汇总返回——缺乏对抗性审视与冲突消解。没有 Debate 环节，各专家观点中的矛盾信号（如技术面看多、估值面看空）无法被系统性暴露和量化，直接交给 Judge 做最终裁决会导致决策偏见。Debate 模块是流水线贯通的关键缺失环节，需要优先补齐。

## What Changes

- **新增 Debate Bounded Context**（`src/modules/debate/`）：实现多空对抗辩论引擎，消费五专家的 `ResearchResult`，通过 LLM 驱动的多空辩论生成结构化的 `DebateOutcome`（含多空论点、风险矩阵、冲突消解结论）。
- **新增 Debate Application 接口**：对外暴露辩论用例，供 Coordinator 通过 Port/Adapter 调用。
- **扩展 Coordinator 编排图**：在 LangGraph 的 `aggregator_node` 之后接入 `debate_node`，将研究汇总结果流转至 Debate 模块，使流水线延伸为 `Research → Aggregator → Debate → END`（Judge 后续接入）。
- **新增 Debate REST 端点**：提供独立的辩论触发与结果查询接口，便于调试和独立测试。

## Capabilities

### New Capabilities

- `debate-bull-bear-engine`：Debate 模块核心能力——接收五专家研究结果，通过 LLM 驱动的结构化多空辩论流程（多头论证 → 空头论证 → 交叉质疑 → 冲突消解），输出 `DebateOutcome`（多空论点摘要、风险矩阵、综合置信度、冲突消解结论）。

### Modified Capabilities

- `coordinator-research-orchestration`：扩展 Coordinator 编排图，在 aggregator 节点之后新增 debate 节点，将研究结果流转至 Debate 模块；新增 `IDebateGateway` Port 和对应 Adapter；更新编排结果 DTO 以包含辩论产出。

## Impact

- **新增代码**：`src/modules/debate/`（domain / application / infrastructure / presentation 四层），预计新增 15-20 个文件。
- **修改代码**：`src/modules/coordinator/`——graph_builder 新增 debate 节点与边、新增 `IDebateGateway` Port、新增 Gateway Adapter、扩展 `ResearchGraphState` 和结果 DTO。
- **依赖**：Debate 模块依赖 `llm_platform` 的 `ILLMProvider` Port（通过 Adapter）驱动辩论 LLM 调用；不直接依赖 `data_engineering`。
- **API**：新增 `/api/v1/debate/` REST 端点；现有 `/api/v1/coordinator/research` 的响应结构将扩展以包含辩论结果。
- **数据库**：本阶段暂不涉及持久化（辩论结果随流水线返回，不落库），后续可按需扩展。
- **测试**：需新增 Debate 模块单元测试与集成测试；Coordinator 编排测试需覆盖含 Debate 节点的完整流水线。
