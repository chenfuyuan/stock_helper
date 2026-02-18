---
title: Financial Auditor Specification
version: 1.0
last_updated: 2026-02-19
module: research
capabilities:
  - financial-audit
source_specs:
  - research-financial-auditor
---

# Financial Auditor Specification

## Purpose

财务审计员能力：基于 data_engineering 提供的硬数据（财务指标）进行定量分析，结合 LLM 进行定性风险排查，输出结构化的财务健康评估（0–100 评分 + 5D 维度分析 JSON），供 Debate/Judge 使用。Research 对 Coordinator 按专家暴露独立 Application 接口，本 spec 仅约束财务审计员。

## Capabilities

| Capability | Description | Source |
|------------|-------------|--------|
| financial-audit | 财务指标分析与健康评估 | research-financial-auditor/spec.md |

## General Conventions

### Requirement Language
- **SHALL** / **MUST**：强制性要求
- **SHOULD**：推荐性要求
- **MAY**：可选要求

### Testing Convention
每个 `#### Scenario:` 在变更交付时须对应至少一个自动化测试用例（单元或集成）；实现顺序可先实现再补测，以完整测试通过为需求完成标准。

---

## capability: financial-audit

> Source: research-financial-auditor/spec.md

财务审计员能力：基于 data_engineering 提供的硬数据（财务指标）进行定量分析，结合 LLM 进行定性风险排查，输出结构化的财务健康评估。

---

## Requirements

### Requirement: 财务审计员暴露独立 Application 接口

Research 模块 SHALL 为财务审计员暴露独立的 Application 层入口（如 `FinancialAuditorService`），供 Coordinator 直接调用。该接口 SHALL NOT 与其他四专家共用同一入口；Coordinator 编排时 SHALL 分别调用各专家的专属 Application 接口。

#### Scenario: Coordinator 调用财务审计员

- **WHEN** Coordinator 需要该标的的财务面评估
- **THEN** Coordinator 调用财务审计员的 Application 接口（入参含 symbol），获得财务审计结果 DTO，且不通过统一的「Research 总入口」

#### Scenario: 接口入参与出参为 DTO

- **WHEN** 调用财务审计员 Application 接口
- **THEN** 入参为 DTO 或值对象（至少包含 symbol），出参为财务审计结果 DTO（对应下方输出契约），不暴露 Research 内部领域模型

---

### Requirement: HTTP 响应体包含 input、output、financial_indicators

财务审计员的 HTTP 接口（如 `GET /api/v1/research/financial-audit`）的响应体 SHALL 与技术分析师接口一致，由**代码塞入**以下字段（非大模型拼接）：`input`（送入大模型的 user prompt）、`output`（大模型原始返回字符串）、`financial_indicators`（财务指标快照，用于填充 prompt 的 `FinancialSnapshotDTO` 序列化结果）。响应体 SHALL 同时包含解析后的审计结果字段（financial_score、signal、confidence、summary_reasoning、dimension_analyses、key_risks、risk_warning）。

#### Scenario: 响应体含 input、output、financial_indicators

- **WHEN** 调用财务审计 HTTP 接口并成功返回
- **THEN** 响应体 SHALL 包含 `input`（字符串）、`output`（字符串）、`financial_indicators`（对象），便于调试与审计追溯

#### Scenario: 与技术分析师接口结构对称

- **WHEN** 比较技术分析师与财务审计员的 HTTP 响应结构
- **THEN** 二者 SHALL 均包含 input、output，且分别包含 `technical_indicators` 与 `financial_indicators`，结构对称

---

### Requirement: 输入契约 — 股票代码与财务数据自动获取

财务审计员 SHALL 接受股票代码（symbol）作为主要输入。系统 SHALL 自动从 data_engineering 获取该标的最近 N 期（默认 5 期）的财务指标数据（`StockFinance` 记录），在 Research 内部构建为「静态财务快照」（当期关键指标）与「历史趋势序列」（多季度时间序列）两部分，作为送入 LLM 的硬数据事实。所有指标数值 SHALL 由 data_engineering 提供的原始财报数据支撑；财务审计员 SHALL NOT 在观点中引用或捏造输入数据中不存在的数值。

#### Scenario: 输入完整时产出有效结果

- **WHEN** 调用方提供有效的 symbol，且 data_engineering 中存在该标的的财务指标数据
- **THEN** 财务审计员返回符合输出契约的 JSON 结果，且 summary_reasoning 中引用的财务指标数值均来自输入数据

#### Scenario: 输入缺失 symbol 时的行为

- **WHEN** 调用方未提供必填输入 symbol（空字符串或 None）
- **THEN** 系统 SHALL 在调用 Application 接口时通过校验或领域异常明确拒绝，并返回可区分的错误信息

#### Scenario: 该标的无财务数据时的行为

- **WHEN** 调用方提供的 symbol 在 data_engineering 中无任何财务指标记录
- **THEN** 系统 SHALL 返回明确的错误信息（如「该标的无财务数据，请先同步」），不将空数据传入 LLM

---

### Requirement: 财务快照构建为 Domain Port、Infrastructure 实现

财务审计员所需的结构化数据（静态快照 + 历史趋势）SHALL 通过 Research Domain 层定义的「构建财务快照」Port（如 `IFinancialSnapshotBuilder`）获得：该 Port 入参为多期财务数据 DTO 列表，出参为与 User Prompt 模板一致的 `FinancialSnapshotDTO`。Port 的具体实现 SHALL 位于 Research 的 Infrastructure 层。

实现 SHALL 包含以下处理：
1. 按 `end_date` 降序排列，提取最新期作为静态快照（盈利能力、每股含金量、资产负债、运营效率指标）。
2. 派生指标计算（如 `quality_ratio = OCFPS / EPS`，EPS 为 0 时标记 N/A）。
3. 历史趋势序列构建（多季度时间序列：gross_margin、roic、fcff、invturn_days、arturn_days 等）。
4. YoY 增速计算（若原始数据不含增速字段，基于相邻同期记录计算；数据不足时标记 N/A）。

Application 层 SHALL 仅依赖该 Port 获取快照，SHALL NOT 直接调用 Infrastructure 中的构建实现。

#### Scenario: 通过 Port 获取财务快照

- **WHEN** Application 编排需要构建财务快照以进行审计分析
- **THEN** 通过注入的快照构建 Port（如 `IFinancialSnapshotBuilder`）传入多期财务数据 DTO 并获取 `FinancialSnapshotDTO`，不直接实例化或引用 Infrastructure 中的构建实现

#### Scenario: 派生指标正确计算

- **WHEN** 快照构建器收到包含 EPS 与 OCFPS 的财务数据
- **THEN** 输出快照中的 `quality_ratio` SHALL 等于 `OCFPS / EPS`（EPS 为 0 时 SHALL 标记为 N/A 而非抛出异常）

#### Scenario: 数据不足时不捏造

- **WHEN** 传入的财务数据仅有 1 期（不足以计算 YoY 增速）
- **THEN** 快照构建器 SHALL 将 YoY 增速字段标记为 N/A，SHALL NOT 生成虚构的增速值

---

### Requirement: 输出契约 — 固定 JSON 结构（5D 审计模型）

财务审计员的产出 SHALL 为固定结构的 JSON（或等价的 DTO），包含：

- `financial_score`（int，0–100，整体财务健康评分）
- `signal`（枚举：STRONG_BULLISH / BULLISH / NEUTRAL / BEARISH / STRONG_BEARISH），与评分区间对应（90–100 = STRONG_BULLISH，75–89 = BULLISH，50–74 = NEUTRAL，30–49 = BEARISH，0–29 = STRONG_BEARISH）
- `confidence`（float，0.0–1.0）
- `summary_reasoning`（审计逻辑摘要，须引用输入中的财务指标读数）
- `dimension_analyses`（list，包含 5 个维度，每个维度含 `dimension`（维度名）、`score`（该维度评分）、`assessment`（简评）、`key_findings`（关键发现列表））
- `key_risks`（list[str]，主要风险标记）
- `risk_warning`（评估被证伪时的关键条件描述）

**解析逻辑 SHALL 内聚到该 Agent**（`agents/financial_auditor/output_parser.py`）。系统 SHALL 使用 pydantic 或等价机制校验并反序列化本 Agent 的 LLM 输出。若解析失败 SHALL **将 LLM 原始输出写入日志（可截断）** 并抛出领域友好异常（`LLMOutputParseError`），不将未校验的字符串作为审计结果返回给调用方。

#### Scenario: 正常返回符合结构的结果

- **WHEN** LLM 返回合法且可解析的 JSON
- **THEN** Application 层返回的 DTO 包含上述七类字段，且 financial_score 在 [0, 100] 内、signal 为五值之一、confidence 在 [0, 1] 内、dimension_analyses 包含 5 个维度

#### Scenario: LLM 返回非 JSON 或格式错误

- **WHEN** LLM 返回内容无法解析为上述结构的 JSON
- **THEN** 系统 SHALL 将 LLM 原始输出写入日志（可截断）、抛出 `LLMOutputParseError`，不将未校验的字符串作为财务审计结果返回给调用方

#### Scenario: financial_score 与 signal 的一致性

- **WHEN** LLM 返回的 financial_score 与 signal 不符合评分区间映射规则
- **THEN** 系统 SHALL 以 financial_score 为准重新映射 signal（或记录警告后接受 LLM 的 signal），确保返回给调用方的结果内部一致

---

### Requirement: 证据驱动与无交易建议

财务审计员的观点（summary_reasoning、dimension_analyses 中的 assessment 与 key_findings）SHALL 直接引用输入中提供的财务指标读数作为证据（例如「ROIC 达 18.5% 且连续三季上升，护城河正在变宽」「OCFPS/EPS 仅为 0.6，盈利含金量存疑」）。财务审计员 SHALL NOT 输出「建议买入」「建议卖出」「立即建仓」等交易指令；该类决策属于 Judge 模块职责。当定量数据与定性判断存在冲突时，输出 SHALL 明确指出该冲突，并 SHALL 相应降低 confidence。

#### Scenario: 观点引用输入财务指标

- **WHEN** 输入包含 ROIC=18.5%、current_ratio=0.8 等数据
- **THEN** summary_reasoning 与 dimension_analyses 中出现的数值或状态描述 SHALL 与输入一致，不得捏造未提供的读数

#### Scenario: 不输出交易建议

- **WHEN** 财务审计员生成 summary_reasoning 与 risk_warning
- **THEN** 输出 SHALL NOT 包含建议买入、建议卖出、立即建仓等交易指令类表述

---

### Requirement: Prompt 内聚于 Agent 且存放于代码外

财务审计员的 System Prompt 与 User Prompt 模板 SHALL 内聚在该专家（agent）的上下文中，且 SHALL NOT 将 prompt 正文硬编码在代码中。Prompt 内容 SHALL 存放在代码库内约定的资源目录（`src/modules/research/agents/financial_auditor/prompts/` 下的 `system.md` 与 `user.md`），由该专家的 Infrastructure 在运行时加载；模板中的占位符（如 `{symbol}`、`{gross_margin}`、`{roic_series}`）SHALL 在代码中用本次调用的财务快照数据填充。

#### Scenario: Prompt 从资源加载

- **WHEN** 财务审计员执行分析流程并需要调用 LLM
- **THEN** 使用的 System Prompt 与 User Prompt 模板来自资源文件（`agents/financial_auditor/prompts/`），而非 Python 源码中的长字符串

#### Scenario: 占位符由代码填充

- **WHEN** 资源文件中的 User Prompt 包含占位符（如 `{symbol}`、`{report_period}`、`{gross_margin}`、`{roic_series}`）
- **THEN** 运行时由代码使用本次调用的财务快照数据填充这些占位符后，再传入 LLM

---

### Requirement: 跨模块与模块内均通过 Port/Application 接口

财务审计员实现 SHALL 仅通过 data_engineering、llm_platform 的 **Application 接口** 获取数据与调用 LLM；SHALL NOT 直接依赖上述模块的领域模型、实体、值对象或 Infrastructure 实现。**Research 内部**对「获取财务数据」「构建财务快照」「调用审计 Agent」的依赖 SHALL 通过 Domain Port 进行，Application 层 SHALL NOT 直接依赖 Infrastructure 实现类。入参/出参 SHALL 使用 DTO 或 Port 约定的抽象类型。

#### Scenario: 获取财务指标数据

- **WHEN** 财务审计员需要财务指标数据以构建快照
- **THEN** 通过 Research 的获取财务数据 Port（`IFinancialDataPort`，其 Adapter 内部调用 data_engineering 的 Application 接口 `GetFinanceForTickerUseCase`）获取 DTO，不直接依赖 data_engineering 的 repository 或 domain 实体

#### Scenario: 调用 LLM

- **WHEN** 财务审计员需要调用大模型生成审计分析
- **THEN** 通过财务审计 Agent Port（`IFinancialAuditorAgentPort`，其实现内部调用 llm_platform 的 Application 接口）传入 system_message 与 prompt，Application 层不直接依赖 llm_platform 的 router、registry 或 adapter 实现类

---

### Requirement: 可测性 — Scenario 与测试一一对应

每个上述 Scenario 在变更交付时 SHALL 对应至少一个自动化测试（单元或集成）；需求完成的验收条件包含「该需求下所有 Scenario 的测试通过」。实现时可采用先实现再补测，不强制测试先行。

#### Scenario: 测试覆盖输入缺失拒绝

- **WHEN** 运行财务审计员相关测试套件
- **THEN** 存在测试用例：传入缺失 symbol 的入参，断言调用被拒绝并返回可区分错误（对应「输入缺失 symbol 时的行为」）

#### Scenario: 测试覆盖无财务数据拒绝

- **WHEN** 运行财务审计员相关测试套件
- **THEN** 存在测试用例：mock 财务数据 Port 返回空列表，断言系统返回明确错误信息（对应「该标的无财务数据时的行为」）

#### Scenario: 测试覆盖 LLM 解析失败

- **WHEN** 运行财务审计员相关测试套件
- **THEN** 存在测试用例：mock LLM 返回非 JSON 或非法结构，断言系统抛出 `LLMOutputParseError`、不返回未校验字符串（对应「LLM 返回非 JSON 或格式错误」）

#### Scenario: 测试覆盖快照构建派生指标

- **WHEN** 运行财务审计员相关测试套件
- **THEN** 存在测试用例：传入已知财务数据，断言快照构建器输出的 quality_ratio、YoY 增速等派生指标计算正确（对应「派生指标正确计算」与「数据不足时不捏造」）
