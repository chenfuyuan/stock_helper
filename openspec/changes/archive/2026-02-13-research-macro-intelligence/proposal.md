# Proposal: Research 模块 — 宏观情报员

## Why

Research 作为「事实工厂」需要五专家之一 **宏观情报员**，负责从**自上而下**的视角，分析宏观经济环境、货币政策、产业政策与行业周期对标的的影响，输出结构化的宏观环境评估。宏观情报员是五专家中唯一以**软情报（Web 搜索）**为主要数据源的角色——已实现的三位专家（技术分析师、财务审计员、估值建模师）均消费 data_engineering 的硬数据，而宏观情报员通过 llm_platform 已有的 `WebSearchService` 获取实时宏观动态，结合 LLM 进行定性分析，实现愿景中「证据驱动：观点必须基于硬数据（DB）或**软情报（搜索）**」的架构承诺。核心信条为 **"自上而下，追踪宏观脉搏"** —— 宏观环境决定行业走向，行业走向影响个股命运；观点必须基于 Web 搜索获取的可查证宏观事实与政策信息，杜绝 LLM 幻觉。

## What Changes

- **新增宏观情报员角色**：以「首席宏观策略师 (Chief Macro Strategist)」人设，采用 **四维宏观扫描框架**（货币与流动性环境 → 产业政策与监管动态 → 宏观经济周期定位 → 行业景气与资金流向）对标的所处的宏观环境进行系统性评估，不做最终交易决策。
- **输入契约**：接受股票代码（symbol）；系统自动：
  1. 从 data_engineering 获取该标的的**股票基础信息**（名称、行业）—— 通过已有的 `GetStockBasicInfoUseCase`。
  2. 基于行业与公司上下文，通过 llm_platform 的 `WebSearchService` 执行**多主题宏观搜索**（货币政策、行业政策、宏观经济指标、行业动态等），获取实时宏观情报。
  搜索查询 SHALL 由代码根据行业上下文动态生成（如"XX行业 宏观政策 2026""央行 货币政策 最新"等）；搜索结果在 Research 内部经过结构化处理后，作为硬证据填入 User Prompt 模板。**这是 Research 模块首次消费 `WebSearchService`**，需在 Research 中新增对应的 Domain Port 与 Infrastructure Adapter。
- **输出契约**：固定 JSON 结构，包含：`macro_environment`（Favorable (有利) / Neutral (中性) / Unfavorable (不利)）、`confidence_score`（0.0–1.0）、`macro_summary`（宏观环境综合判断，须引用搜索证据）、`dimension_analyses`（四维各自的评估、评分与关键发现）、`key_opportunities`（宏观层面的机会列表）、`key_risks`（宏观层面的风险列表）、`information_sources`（引用的信息来源 URL 列表，用于溯源审计）。
- **绝对约束**：证据驱动（观点必须引用 Web 搜索获取的具体信息作为证据，并标注来源 URL）；不输出「建议买入/卖出」等交易指令；LLM 不得捏造未搜索到的宏观数据或政策信息；当搜索结果不足或信息过时时，须明确声明"信息有限"并降低置信度。
- **集成方式**：宏观情报员作为 Research 内一个独立分析单元，依赖 data_engineering（股票基础信息）、llm_platform（Web 搜索 + LLM 调用）的 **Application 接口**。本变更仅暴露宏观情报员专属入口（如 `MacroIntelligenceService`），Coordinator 直接调用该接口。
- **Prompt 归属与存放**：System Prompt 与 User Prompt 模板**内聚在该专家中**，存放在 `agents/macro_intelligence/prompts/`（`system.md` 与 `user.md`），运行时加载，模板占位符在代码中用搜索结果与股票基础信息填充。Prompt 内容已预先定义（见本变更目录下的 `system.md` 与 `user.md`）。
- **无上游前置依赖变更**：与财务审计员（需新增 data_engineering 查询接口）和估值建模师（需新增估值日线查询 + bps 字段）不同，本变更**不需修改 data_engineering 或 llm_platform 的现有实现**。`GetStockBasicInfoUseCase`、`WebSearchService`、`LLMService` 均已就绪。
- **实现与验证方式**：Spec 中每个 Scenario 在变更完成时须有对应自动化测试；实现顺序灵活，交付以**完整测试通过**为完成标准。

## Capabilities

### New Capabilities

- **`research-macro-intelligence`**：宏观情报员能力。定义输入（股票代码 → 系统获取股票基础信息 + 执行宏观主题 Web 搜索）、输出（MacroIntelligenceResult JSON 结构）、四维宏观扫描框架（货币/流动性、产业政策/监管、宏观经济周期、行业景气/资金流向）、与 LLM 的 Prompt 契约（证据驱动/来源标注/输出纯 JSON），以及搜索结果的结构化处理规约。每个需求下的 Scenario 在交付时须有对应自动化测试。

### Modified Capabilities

- （无。技术分析师、财务审计员与估值建模师的能力 spec 不受影响；四者为独立专家，各自有独立 Application 接口。）

## Impact

- **代码**：在 `src/modules/research/` 下新增宏观情报员相关 Domain（输入/输出 DTO）、Application 服务（编排股票信息获取 + Web 搜索 + 宏观上下文构建 + LLM 调用 + 解析）、Domain Port（`IMacroDataPort`、`IMacroContextBuilder`、`IMacroIntelligenceAgentPort`）及 Infrastructure 适配。新增 `agents/macro_intelligence/` 目录含 Prompt 资源与输出解析器。
- **依赖**：Research 依赖 data_engineering（股票基础信息，通过已有 `GetStockBasicInfoUseCase`）、llm_platform（Web 搜索通过已有 `WebSearchService` + LLM 调用通过已有 `LLMService`）；不依赖 Coordinator/Debate/Judge。**无需修改 data_engineering 或 llm_platform 的现有实现**。
- **API/系统**：宏观情报员产出为 ResearchReport 的一个片段。Research 对 Coordinator 按专家暴露独立接口（本变更仅宏观情报员一个接口）。若提供 HTTP 接口，响应体 SHALL 与其他三专家一致：包含 input、output、macro_indicators（代码塞入的宏观情报上下文，便于调试与审计追溯）。
- **测试与可验证性**：Spec 中所有 Scenario 在交付时须有对应自动化测试；交付完成以「完整测试通过 + 无跨模块直接依赖」为验收条件。
- **非目标**：本变更不实现 Research 的「并行五专家」编排、不实现 Debate/Judge；不实现剩余专家（催化剂侦探）；不改变现有三专家的实现。
