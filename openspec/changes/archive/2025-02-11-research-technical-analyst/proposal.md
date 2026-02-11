# Proposal: Research 模块 — 技术分析师

## Why

Research 作为「事实工厂」需要五专家之一**技术分析师**，将预计算的技术指标与图表形态整合为**证据驱动的技术面观点**，为后续 Debate/Judge 提供可引用的市场叙事与关键价位，而非交易指令。技术分析遵循「市场行为包容一切信息、趋势延续」的信条，且必须仅基于给定硬数据输出观点，以符合项目「证据驱动、杜绝幻觉」的架构哲学。

## What Changes

- **新增技术分析师角色**：以 CMT 持证分析师人设，仅基于预计算指标与形态做解读，不做最终交易决策。
- **输入契约**：接受目标资产信息（ticker、analysis_date、current_price）及硬数据事实：趋势与均线（MA 位置、排列、ADX）、动量与震荡（RSI、MACD、KDJ）、量能（成交量状态、OBV）、形态识别结果（K 线形态、支撑/阻力位）。所有数值由上游或本模块内量化引擎预计算，分析师不捏造数据。
- **输出契约**：固定 JSON 结构：`signal`（BULLISH/BEARISH/NEUTRAL）、`confidence`（0.0–1.0）、`summary_reasoning`（简练分析逻辑并引用指标）、`key_technical_levels`（support/resistance）、`risk_warning`（证伪关键点位）。
- **绝对约束**：证据驱动（观点必须引用输入中的指标读数）；不输出「建议买入/卖出」等交易指令；使用标准中文技术术语；指标冲突时明确背离并降低置信度。
- **集成方式**：技术分析师作为 Research 内一个分析单元，依赖 data_engineering、llm_platform 的 **Application 接口** 获取数据与调用 LLM；产出纳入 `ResearchReport` 的技术分析片段。**Research 提供给 Coordinator 的接口按专家独立**：五专家不共用同一 Application 入口，Coordinator 分别调用各专家的专属接口（如技术分析师对应 `TechnicalAnalystService`）。
- **Prompt 归属与存放**：每个专家的 System/User Prompt **内聚在该专家（agent）中**，但**不存放在代码里**；存放在资源目录（如按专家分目录的 prompt 文件），运行时加载，模板占位符在代码中填充。
- **实现与验证方式**：Spec 中的每个 Scenario 在变更完成时须有对应自动化测试；实现顺序可先实现再补测，交付以**完整测试通过**为完成标准（见 [tech-standards.md § OpenSpec 与测试约定](../../specs/tech-standards.md)）。

## Capabilities

### New Capabilities

- **research-technical-analyst**：技术分析师能力。定义输入（预计算技术指标与形态）、输出（上述 JSON 结构）、与 LLM 的 Prompt 契约（Role/Objective/Critical Constraints/Output Format），以及如何接入 ResearchReport。不包含「由谁计算指标」的实现细节，仅约定分析师消费的数据形态与产出形态。**每个需求下的 Scenario 在交付时须有对应自动化测试**。

### Modified Capabilities

- （无。当前 `openspec/specs/` 下无 Research 相关能力 spec，无需求级变更。）

## Impact

- **代码**：新建 `src/modules/research/`，至少包含技术分析师相关 Domain（值对象/输出 DTO）、Application 服务（编排指标获取 + LLM 调用 + 解析）、对 data_engineering 与 llm_platform 的 Port 依赖及 Infrastructure 适配。
- **依赖**：Research 依赖 data_engineering（行情/日线等）、llm_platform（LLM 调用）；不依赖 Coordinator/Debate/Judge。
- **API/系统**：技术分析师产出为 ResearchReport 的一部分。Research 对 Coordinator **按专家暴露独立 Application 接口**（本变更仅技术分析师一个接口），无统一的「五专家共用」入口；无对外 HTTP API 变更（除非后续单独为 Research 增加接口）。
- **测试与可验证性**：Spec 中所有 Scenario 在交付时须有对应自动化测试；实现可先实现再补测；交付完成以「完整测试通过 + 无跨模块直接依赖」为验收条件。
- **非目标**：本变更不实现 Research 的「并行五专家」编排、不实现 Debate/Judge；不规定指标计算必须落在 data_engineering 或 Research 内部（可在 design 中定界）。
