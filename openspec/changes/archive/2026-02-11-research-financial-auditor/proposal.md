# Proposal: Research 模块 — 财务审计员

## Why

Research 作为「事实工厂」需要五专家之一 **财务审计员**，基于 data_engineering 提供的硬数据（财务指标）进行**定量分析**，并结合 LLM 进行**定性风险排查**，输出结构化的财务健康评估。财务审计员不预测股价，只评估公司的「身体健康状况」，为后续 Debate/Judge 提供可引用的财务面证据。核心信条为 **"Trust, but Verify"** —— 观点必须由 data_engineering 提供的原始财报数据支撑，杜绝 LLM 幻觉。

## What Changes

- **新增财务审计员角色**：以「首席财务官 (CFO) 兼法务审计长」人设，采用 **5D 审计模型**（盈利含金量、运营效率与造假侦测、资本回报与护城河、偿债与生存能力、成长加速度）对公司进行交叉验证式财务审计，不做最终交易决策。
- **输入契约**：接受股票代码（symbol）；系统自动从 data_engineering 获取该标的的财务指标数据（多期 `StockFinance` 记录），在 Research 内部构建为「静态财务快照」（当期关键指标）与「历史趋势序列」（多季度时间序列）两部分，作为送入 LLM 的硬数据事实。所有指标数值由 data_engineering 提供，审计员不捏造数据。
- **输出契约**：固定 JSON 结构，至少包含：`financial_score`（0–100 整体评分）、`signal`（STRONG_BULLISH / BULLISH / NEUTRAL / BEARISH / STRONG_BEARISH）、`confidence`（0.0–1.0）、`summary_reasoning`（审计逻辑摘要，须引用输入中的财务指标读数）、`dimension_analyses`（5 个维度各自的评分与发现）、`key_risks`（主要风险标记列表）、`risk_warning`（评估被证伪时的关键条件描述）。
- **绝对约束**：证据驱动（观点必须引用输入中的财报指标读数）；不输出「建议买入/卖出」等交易指令；使用标准中文财务术语；当定量数据与定性判断冲突时明确指出并降低置信度。
- **集成方式**：财务审计员作为 Research 内一个独立分析单元，依赖 data_engineering（财务指标）、llm_platform（LLM 调用）的 **Application 接口**。Research 按专家暴露独立 Application 接口：本变更仅暴露财务审计员专属入口（如 `FinancialAuditorService`），Coordinator 直接调用该接口。
- **Prompt 归属与存放**：System Prompt 与 User Prompt 模板**内聚在该专家（agent）中**，但**不存放在代码里**；存放在资源目录（`agents/financial_auditor/prompts/`），运行时加载，模板占位符在代码中填充。Prompt 内容已预先定义（见 `system.md` 与 `user.md`）。
- **data_engineering 前置依赖**：当前 data_engineering 的 `IFinancialDataRepository` 仅有 `save_all` 写入接口，无读取/查询能力。本变更需在 data_engineering 中新增只读查询用例（如 `GetFinanceForTickerUseCase`），按标的代码与日期区间返回 `StockFinance` DTO 列表，供 Research 消费。
- **财务数据处理**：从 data_engineering 获取的原始 `StockFinance` 多期记录需在 Research 内部经过处理（通过 Domain Port + Infrastructure 实现），构建为与 User Prompt 模板一致的「静态快照 + 历史趋势」结构，包含派生指标（如 quality_ratio = OCFPS/EPS、YoY 增速等）。
- **实现与验证方式**：Spec 中每个 Scenario 在变更完成时须有对应自动化测试；实现顺序灵活，交付以**完整测试通过**为完成标准。

## Capabilities

### New Capabilities

- **`research-financial-auditor`**：财务审计员能力。定义输入（股票代码 → 系统获取财务指标）、输出（FinancialAuditResult JSON 结构）、5D 审计框架、与 LLM 的 Prompt 契约（Role/5D Framework/Scoring Protocol/Output Constraint），以及如何接入 ResearchReport。每个需求下的 Scenario 在交付时须有对应自动化测试。

### Modified Capabilities

- （无。技术分析师的能力 spec 不受影响；二者为独立专家，各自有独立 Application 接口。）

## Impact

- **代码**：在 `src/modules/research/` 下新增财务审计员相关 Domain（输入/输出 DTO）、Application 服务（编排财务数据获取 + 数据处理 + LLM 调用 + 解析）、Domain Port（`IFinancialDataPort`、`IFinancialSnapshotBuilder`、`IFinancialAuditorAgentPort`）及 Infrastructure 适配。新增 `agents/financial_auditor/` 目录含 Prompt 资源与输出解析器。
- **依赖**：Research 依赖 data_engineering（财务指标查询）、llm_platform（LLM 调用）；不依赖 Coordinator/Debate/Judge。需在 data_engineering 中新增财务指标只读查询 Application 接口（`GetFinanceForTickerUseCase`）和 Repository 读方法。
- **API/系统**：财务审计员产出为 ResearchReport 的一个片段。Research 对 Coordinator 按专家暴露独立接口（本变更仅财务审计员一个接口）。若提供 HTTP 接口，响应体 SHALL 与技术分析师一致：包含 input、output、financial_indicators（代码塞入，便于调试与审计追溯），与技术分析师的 technical_indicators 对应。
- **测试与可验证性**：Spec 中所有 Scenario 在交付时须有对应自动化测试；实现可先实现再补测；交付完成以「完整测试通过 + 无跨模块直接依赖」为验收条件。
- **非目标**：本变更不实现 Research 的「并行五专家」编排、不实现 Debate/Judge；不实现其余四专家；不改变现有技术分析师的实现。
