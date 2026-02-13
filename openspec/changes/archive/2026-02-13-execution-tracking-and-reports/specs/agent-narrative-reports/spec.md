## ADDED Requirements

### Requirement: Agent 双输出模式

所有 9 个 Agent（5 个 Research 专家 + Bull/Bear/Resolution + Judge Verdict）的 LLM 调用 SHALL 在单次调用中同时产出结构化 JSON 数据和叙述性中文报告。

结构化 JSON 中 MUST 新增 `narrative_report` 字段（string 类型），包含面向人类的中文分析报告。

#### Scenario: 技术分析师双输出

- **WHEN** 技术分析师 Agent 完成分析
- **THEN** 返回的 `TechnicalAnalysisResultDTO` 包含原有全部结构化字段（signal、confidence、summary_reasoning 等）以及新增的 `narrative_report` 字段，narrative_report 为非空中文文本

#### Scenario: 裁决 Agent 双输出

- **WHEN** Judge Verdict Agent 完成裁决
- **THEN** 返回的 `VerdictResult` 包含原有全部结构化字段（action、position_percent、confidence 等）以及新增的 `narrative_report` 字段

### Requirement: 叙述性报告内容规范

`narrative_report` SHALL 使用中文撰写，内容 MUST 包含：核心结论、关键论据（引用具体数据或事实）、风险提示、置信度说明。报告应面向具备基本投资知识的读者，语言简洁专业。

#### Scenario: 报告内容完整性

- **WHEN** 任意 Agent 生成 narrative_report
- **THEN** 报告中包含明确的核心结论（如"看多"/"看空"/"中性"）、至少一条具体论据、风险提示部分

#### Scenario: 报告语言

- **WHEN** 任意 Agent 生成 narrative_report
- **THEN** 报告全文为中文（标点、术语可保留英文原词如 PE、ROE 等）

### Requirement: Research 五专家 DTO 扩展

Research 模块的 5 个专家结果 DTO（`TechnicalAnalysisResultDTO`、`FinancialAuditResultDTO`、`ValuationResultDTO`、`MacroIntelligenceResultDTO`、`CatalystDetectiveResultDTO`）SHALL 各新增 `narrative_report: str` 字段。

#### Scenario: 财务审计员 DTO

- **WHEN** 财务审计员 Agent 返回分析结果
- **THEN** `FinancialAuditResultDTO` 包含 `narrative_report` 字段，类型为 str，内容为中文财务分析报告

#### Scenario: 估值建模师 DTO

- **WHEN** 估值建模师 Agent 返回分析结果
- **THEN** `ValuationResultDTO` 包含 `narrative_report` 字段，类型为 str，内容为中文估值分析报告

### Requirement: Debate 三 Agent DTO 扩展

Debate 模块的 3 个 Agent 结果 DTO（`BullArgument`、`BearArgument`、`ResolutionResult`）SHALL 各新增 `narrative_report: str` 字段。

#### Scenario: Bull Advocate 报告

- **WHEN** Bull Advocate Agent 完成多头论证
- **THEN** `BullArgument` 包含 `narrative_report` 字段，内容为中文多头分析报告，包含核心看多逻辑和风险承认

#### Scenario: Resolution 报告

- **WHEN** Resolution Agent 完成冲突消解
- **THEN** `ResolutionResult` 包含 `narrative_report` 字段，内容为中文综合研判报告，平衡多空观点

### Requirement: Judge Verdict DTO 扩展

Judge 模块的 `VerdictResult` SHALL 新增 `narrative_report: str` 字段。

#### Scenario: 最终裁决报告

- **WHEN** Judge Verdict Agent 完成最终裁决
- **THEN** `VerdictResult` 包含 `narrative_report` 字段，内容为中文投资决策报告，包含操作建议、仓位建议、止损止盈策略及理由

### Requirement: Output Parser 兼容

各 Agent 的 output_parser SHALL 正确解析包含 `narrative_report` 字段的 JSON 输出。若 LLM 未返回 `narrative_report` 字段，parser SHALL 提供默认空字符串，不抛出解析异常。

#### Scenario: 正常解析

- **WHEN** LLM 返回的 JSON 包含 `narrative_report` 字段
- **THEN** output_parser 正确提取该字段并填入 DTO

#### Scenario: 缺失 narrative_report 的降级

- **WHEN** LLM 返回的 JSON 不包含 `narrative_report` 字段（兼容旧格式）
- **THEN** output_parser 将 `narrative_report` 设为空字符串，其余字段正常解析，不抛出异常

### Requirement: Prompt 改造

各 Agent 的 Prompt 模板 SHALL 更新，在 JSON 输出要求中新增 `narrative_report` 字段的说明，明确告知 LLM 同时生成结构化数据和叙述性中文报告。

#### Scenario: Prompt 包含 narrative_report 指令

- **WHEN** 审查任意 Agent 的 prompt 模板
- **THEN** prompt 中包含对 `narrative_report` 字段的格式要求和内容要求（核心结论、论据、风险、置信度）
