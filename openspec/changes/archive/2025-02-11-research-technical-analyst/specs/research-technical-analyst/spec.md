# Spec: research-technical-analyst

技术分析师能力：将预计算的技术指标与形态整合为证据驱动的技术面观点（结构化 JSON），供 Debate/Judge 使用。Research 对 Coordinator 按专家暴露独立 Application 接口，本 spec 仅约束技术分析师。

**测试约定**：每个 `#### Scenario:` 在变更**交付时**须对应至少一个自动化测试用例（单元或集成）；实现顺序可先实现再补测，以完整测试通过为需求完成标准。

---

## ADDED Requirements

### Requirement: 技术分析师暴露独立 Application 接口

Research 模块 SHALL 为技术分析师暴露独立的 Application 层入口（例如 `TechnicalAnalystService` 或 `RunTechnicalAnalysisUseCase`），供 Coordinator 直接调用。该接口 SHALL NOT 与其他四专家共用同一入口；Coordinator 编排时 SHALL 分别调用各专家的专属 Application 接口。

#### Scenario: Coordinator 调用技术分析师

- **WHEN** Coordinator 需要该标的的技术面观点
- **THEN** Coordinator 调用技术分析师的 Application 接口（入参含 ticker、analysis_date），获得技术分析结果 DTO，且不通过统一的「Research 总入口」

#### Scenario: 接口入参与出参为 DTO

- **WHEN** 调用技术分析师 Application 接口
- **THEN** 入参为 DTO 或值对象（至少包含 ticker、analysis_date），出参为技术分析结果 DTO（对应下方输出契约），不暴露 Research 内部领域模型

---

### Requirement: 输入契约 — 目标资产与预计算硬数据

技术分析师 SHALL 接受以下输入：目标资产信息（ticker、analysis_date、current_price）及硬数据事实：趋势与均线（MA 位置与排列、ADX）、动量与震荡（RSI、MACD、KDJ）、量能（成交量状态、OBV）、形态识别结果（K 线形态列表、支撑位与阻力位）。所有指标与形态数值 SHALL 由上游或本模块内预计算提供；**本模块内时，指标 SHALL 通过 Domain 定义的指标计算 Port（入参日线 DTO、出参指标快照）获得，该 Port 的具体实现在 Infrastructure 层，MAY 依赖第三方库**。分析师 SHALL NOT 在观点中引用或捏造输入中不存在的数值。

#### Scenario: 输入完整时产出有效结果

- **WHEN** 调用方提供完整的目标资产信息与预计算指标/形态数据
- **THEN** 技术分析师返回符合输出契约的 JSON 结果，且 summary_reasoning 中引用的数值均来自输入

#### Scenario: 输入缺失关键字段时的行为

- **WHEN** 调用方未提供必填输入（如 ticker 或 analysis_date）
- **THEN** 系统 SHALL 在调用 Application 接口时通过校验或领域异常明确拒绝，并返回可区分的错误信息

---

### Requirement: 技术指标计算为 Domain Port、Infrastructure 实现

技术分析师所需的技术指标（RSI、MA、MACD、KDJ、ADX、OBV 及形态/支撑阻力）SHALL 可通过 Research Domain 层定义的「计算技术指标」Port 获得：该 Port 入参为日线数据（DTO），出参为与输入契约一致的技术指标快照。Port 的具体实现 SHALL 位于 Research 的 Infrastructure 层；实现 MAY 依赖第三方库（如 ta-lib、pandas）。Application 层 SHALL 仅依赖该 Port 获取指标快照，SHALL NOT 直接调用 Infrastructure 中的计算实现类或第三方库。

#### Scenario: 通过 Port 获取指标快照

- **WHEN** Application 编排需要技术指标以进行技术分析
- **THEN** 通过注入的指标计算 Port（如 IIndicatorCalculator）传入日线 DTO 并获取指标快照，不直接实例化或引用 Infrastructure 中的计算实现或第三方库

#### Scenario: 实现可依赖第三方库

- **WHEN** Research 模块的指标计算 Port 由 Infrastructure 提供实现
- **THEN** 该实现 MAY 依赖 ta-lib、pandas、numpy 等第三方库；替换或升级实现时 Domain Port 契约与 Application 层调用方式不变

---

### Requirement: 输出契约 — 固定 JSON 结构

技术分析师的产出 SHALL 为固定结构的 JSON（或等价的 DTO），包含：`signal`（枚举：BULLISH / BEARISH / NEUTRAL）、`confidence`（浮点数 0.0–1.0）、`summary_reasoning`（简练分析逻辑，须引用输入中的指标读数）、`key_technical_levels`（含 `support`、`resistance` 两个关键价位）、`risk_warning`（观点被证伪时对应的关键点位描述）。**各 Agent 的 JSON 格式可能不同，解析逻辑 SHALL 内聚到该 Agent**（如技术分析师为 `agents/technical_analyst/output_parser.py`）。系统 SHALL 使用 pydantic 或等价机制校验并反序列化本 Agent 的 LLM 输出。若解析失败 SHALL **将 LLM 原始输出写入日志（可截断）**并抛出领域友好异常或返回明确错误结果，便于排查。

#### Scenario: 正常返回符合结构的结果

- **WHEN** LLM 返回合法且可解析的 JSON
- **THEN** Application 层返回的 DTO 包含上述五类字段，且 signal 为三值之一、confidence 在 [0, 1] 内

#### Scenario: LLM 返回非 JSON 或格式错误

- **WHEN** LLM 返回内容无法解析为上述结构的 JSON
- **THEN** 系统 SHALL 将 LLM 原始输出写入日志（可截断）、记录日志并抛出或返回明确错误，不将未校验的字符串作为技术分析结果返回给调用方

---

### Requirement: 证据驱动与无交易建议

技术分析师的观点（summary_reasoning）SHALL 直接引用输入中提供的指标读数作为证据（例如「RSI 达 82 进入超买区」）。技术分析师 SHALL NOT 输出「建议买入」「建议卖出」「立即通过」等交易指令；该类决策属于 Judge 模块职责。当指标之间存在冲突或背离时，输出 SHALL 明确指出该背离，并 SHALL 相应降低 confidence。

#### Scenario: 观点引用输入指标

- **WHEN** 输入包含 RSI=75、MA 金叉等数据
- **THEN** summary_reasoning 中出现的数值或状态描述 SHALL 与输入一致，不得捏造未提供的读数

#### Scenario: 不输出交易建议

- **WHEN** 技术分析师生成 summary_reasoning 与 risk_warning
- **THEN** 输出 SHALL NOT 包含建议买入、建议卖出、立即建仓等交易指令类表述

---

### Requirement: Prompt 内聚于 Agent 且存放于代码外

技术分析师的 System Prompt 与 User Prompt 模板 SHALL 内聚在该专家（agent）的上下文中，且 SHALL NOT 将 prompt 正文硬编码在代码中。Prompt 内容 SHALL 存放在代码库内约定的资源目录（如按专家分目录的 `.md` 或 `.txt` 文件），由该专家的 Application 或 Infrastructure 在运行时加载；模板中的占位符（如 `{ticker}`、`{rsi_value}`）SHALL 在代码中填充。

#### Scenario: Prompt 从资源加载

- **WHEN** 技术分析师执行分析流程并需要调用 LLM
- **THEN** 使用的 System Prompt 与 User Prompt 模板来自资源文件（或通过 Port 注入的资源加载器），而非 Python 源码中的长字符串

#### Scenario: 占位符由代码填充

- **WHEN** 资源文件中的 User Prompt 包含占位符（如 `{ticker}`、`{analysis_date}`、`{rsi_value}`）
- **THEN** 运行时由代码使用本次调用的输入数据填充这些占位符后，再传入 LLM

---

### Requirement: 跨模块与模块内均通过 Port/Application 接口

技术分析师实现 SHALL 仅通过 data_engineering、llm_platform 的 **Application 接口** 获取数据与调用 LLM；SHALL NOT 直接依赖上述模块的领域模型、实体、值对象或 Infrastructure 实现。**Research 内部**对「获取日线」「计算技术指标」「调用分析 Agent」的依赖 SHALL 通过 Domain Port 进行，Application 层 SHALL NOT 直接依赖 Infrastructure 实现类。入参/出参 SHALL 使用 DTO 或 Port 约定的抽象类型。

#### Scenario: 获取行情或日线数据

- **WHEN** 技术分析师需要日线或行情数据以计算指标或填充 Prompt
- **THEN** 通过 Research 的获取日线 Port（其 Adapter 内部调用 data_engineering 的 Application 接口，如 GetDailyBarsForTicker）获取 DTO，不直接依赖 data_engineering 的 repository 或 domain 实体

#### Scenario: 调用 LLM

- **WHEN** 技术分析师需要调用大模型生成分析文本
- **THEN** 通过技术分析 Agent Port（其实现内部调用 llm_platform 的 Application 接口）或等价 Port 传入 system_message 与 prompt，Application 层不直接依赖 llm_platform 的 router、registry 或 adapter 实现类

---

### Requirement: 可测性 — Scenario 与测试一一对应

每个上述 Scenario 在变更交付时 SHALL 对应至少一个自动化测试（单元或集成）；需求完成的验收条件包含「该需求下所有 Scenario 的测试通过」。实现时可采用先实现再补测，不强制测试先行。

#### Scenario: 测试覆盖输入缺失拒绝

- **WHEN** 运行技术分析师相关测试套件
- **THEN** 存在测试用例：传入缺失 ticker 或 analysis_date 的入参，断言调用被拒绝并返回可区分错误（对应「输入缺失关键字段时的行为」）

#### Scenario: 测试覆盖 LLM 解析失败

- **WHEN** 运行技术分析师相关测试套件
- **THEN** 存在测试用例：mock LLM 返回非 JSON 或非法结构，断言系统记录日志并抛出或返回明确错误、不返回未校验字符串（对应「LLM 返回非 JSON 或格式错误」）
