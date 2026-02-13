# Spec: research-valuation-modeler

估值建模师能力：剥离市场情绪，仅基于基本面数据与预计算估值模型（历史分位点、PEG、格雷厄姆数字），计算标的的「内在价值」与「安全边际」，输出结构化的估值判断（Undervalued / Fair / Overvalued + 内在价值区间 JSON），供 Debate/Judge 使用。Research 对 Coordinator 按专家暴露独立 Application 接口，本 spec 仅约束估值建模师。

**核心特点**：所有估值模型的数值计算在代码中预先完成（分位点、PEG、Graham Number、Safety Margin），LLM 仅做定性解读与综合判断，**禁止自行计算**。

**测试约定**：每个 `#### Scenario:` 在变更**交付时**须对应至少一个自动化测试用例（单元或集成）；实现顺序可先实现再补测，以完整测试通过为需求完成标准。

---

## ADDED Requirements

### Requirement: 估值建模师暴露独立 Application 接口

Research 模块 SHALL 为估值建模师暴露独立的 Application 层入口（如 `ValuationModelerService`），供 Coordinator 直接调用。该接口 SHALL NOT 与其他四专家共用同一入口；Coordinator 编排时 SHALL 分别调用各专家的专属 Application 接口。

#### Scenario: Coordinator 调用估值建模师

- **WHEN** Coordinator 需要该标的的估值面评估
- **THEN** Coordinator 调用估值建模师的 Application 接口（入参含 symbol），获得估值结果 DTO，且不通过统一的「Research 总入口」

#### Scenario: 接口入参与出参为 DTO

- **WHEN** 调用估值建模师 Application 接口
- **THEN** 入参为 DTO 或值对象（至少包含 symbol），出参为估值结果 DTO（对应下方输出契约），不暴露 Research 内部领域模型

---

### Requirement: Presentation 层 REST 路由

Research 模块 SHALL 为估值建模师暴露 HTTP REST 接口（路由路径如 `GET /api/v1/research/valuation-model`），位于 `src/modules/research/presentation/rest/` 下，与技术分析师（`technical_analyst_routes.py`）和财务审计员（`financial_auditor_routes.py`）同级。该路由 SHALL 通过 FastAPI 依赖注入装配 `ValuationModelerService` 所需的全部 Port 实现（`IValuationDataPort`、`IValuationSnapshotBuilder`、`IValuationModelerAgentPort`），并在路由函数中调用 `ValuationModelerService.run(symbol)`。

路由 SHALL 处理以下异常并返回对应 HTTP 状态码：
- `BadRequestException` → 400
- `LLMOutputParseError` → 422
- 其他未预期异常 → 500（记录日志）

#### Scenario: HTTP 接口可正常调用

- **WHEN** 发送 `GET /api/v1/research/valuation-model?symbol=000001.SZ` 请求
- **THEN** 系统 SHALL 通过依赖注入装配服务并返回估值结果，HTTP 状态码为 200

#### Scenario: symbol 缺失或无效时返回 400

- **WHEN** 发送请求时 symbol 为空或缺失
- **THEN** 系统 SHALL 返回 HTTP 400，响应体包含可区分的错误信息

#### Scenario: LLM 解析失败时返回 422

- **WHEN** 大模型返回无法解析的内容
- **THEN** 系统 SHALL 返回 HTTP 422，响应体包含解析失败信息

---

### Requirement: HTTP 响应体包含 input、output、valuation_indicators

估值建模师 HTTP 接口的响应体 SHALL 与技术分析师/财务审计员接口一致，由**代码塞入**以下字段（非大模型拼接）：`input`（送入大模型的 user prompt）、`output`（大模型原始返回字符串）、`valuation_indicators`（估值快照，用于填充 prompt 的 `ValuationSnapshotDTO` 序列化结果）。响应体 SHALL 同时包含解析后的估值结果字段（valuation_verdict、confidence_score、estimated_intrinsic_value_range、key_evidence、risk_factors、reasoning_summary）。

#### Scenario: 响应体含 input、output、valuation_indicators

- **WHEN** 调用估值建模 HTTP 接口并成功返回
- **THEN** 响应体 SHALL 包含 `input`（字符串）、`output`（字符串）、`valuation_indicators`（对象），便于调试与审计追溯

#### Scenario: 与其他专家接口结构对称

- **WHEN** 比较技术分析师、财务审计员与估值建模师的 HTTP 响应结构
- **THEN** 三者 SHALL 均包含 input、output，且分别包含 `technical_indicators`、`financial_indicators`、`valuation_indicators`，结构对称

---

### Requirement: 输入契约 — 股票代码与多源数据自动获取

估值建模师 SHALL 接受股票代码（symbol）作为主要输入。系统 SHALL 自动从 data_engineering 获取该标的的三类数据：
1. **股票基础信息**：名称（stock_name）、行业（industry）、third_code。
2. **最新市场估值数据**：当前价格（close）、总市值（total_mv）、PE-TTM、PB、PS-TTM、股息率（dv_ratio）。
3. **历史估值时序数据**：过去约 3 年交易日的 PE-TTM、PB、PS-TTM 数据，用于分位点计算。
4. **财务指标数据**：最近 N 期财务指标（EPS、BPS、ROE、毛利率、净利率、资产负债率等），用于 PEG 计算、Graham 计算和质量体检。

所有指标数值 SHALL 由 data_engineering 提供的原始数据支撑；估值建模师 SHALL NOT 在观点中引用或捏造输入数据中不存在的数值。

#### Scenario: 输入完整时产出有效结果

- **WHEN** 调用方提供有效的 symbol，且 data_engineering 中存在该标的的股票信息、市场行情和财务数据
- **THEN** 估值建模师返回符合输出契约的 JSON 结果，且 key_evidence 和 reasoning_summary 中引用的数值均来自输入数据

#### Scenario: 输入缺失 symbol 时的行为

- **WHEN** 调用方未提供必填输入 symbol（空字符串或 None）
- **THEN** 系统 SHALL 在调用 Application 接口时通过校验或领域异常明确拒绝，并返回可区分的错误信息

#### Scenario: 该标的不存在时的行为

- **WHEN** 调用方提供的 symbol 在 data_engineering 中无对应股票基础信息
- **THEN** 系统 SHALL 返回明确的错误信息（如「该标的不存在」），不继续后续数据获取

#### Scenario: 该标的无财务数据时的行为

- **WHEN** 调用方提供的 symbol 对应的标的无任何财务指标记录
- **THEN** 系统 SHALL 返回明确的错误信息（如「该标的无财务数据，请先同步」），不将空数据传入预计算

---

### Requirement: 估值快照构建为 Domain Port、Infrastructure 实现

估值建模师所需的结构化数据（估值快照）SHALL 通过 Research Domain 层定义的「构建估值快照」Port（如 `IValuationSnapshotBuilder`）获得：该 Port 入参为 `StockOverviewInput`（基础信息 + 最新市场数据）、`List[ValuationDailyInput]`（历史估值日线）、`List[FinanceRecordInput]`（财务指标数据），出参为与 User Prompt 模板一致的 `ValuationSnapshotDTO`。Port 的具体实现 SHALL 位于 Research 的 Infrastructure 层。Application 层 SHALL 仅依赖该 Port 获取快照，SHALL NOT 直接调用 Infrastructure 中的构建实现。

#### Scenario: 通过 Port 获取估值快照

- **WHEN** Application 编排需要构建估值快照以进行估值分析
- **THEN** 通过注入的快照构建 Port（如 `IValuationSnapshotBuilder`）传入三类数据并获取 `ValuationSnapshotDTO`，不直接实例化或引用 Infrastructure 中的构建实现

---

### Requirement: 预计算模型 — 历史分位点

快照构建器 SHALL 基于历史估值日线数据计算 PE-TTM、PB、PS-TTM 的历史百分位排名。算法：`percentile = (当前值在有效序列中的排名 / 有效序列长度) × 100`（四舍五入到整数），有效序列 SHALL 跳过 None / 负值 / 0 值。历史数据默认取最近 3 年（约 750 个交易日）。

#### Scenario: 分位点正确计算

- **WHEN** 快照构建器收到包含 3 年有效 PE/PB/PS 历史数据的估值日线列表
- **THEN** 输出快照中的 `pe_percentile`、`pb_percentile`、`ps_percentile` SHALL 为当前值在有效历史序列中的百分位排名（0–100 整数）

#### Scenario: 历史数据含负值或缺失值

- **WHEN** 历史估值日线中部分 PE-TTM 为 None 或负值（如亏损公司）
- **THEN** 快照构建器 SHALL 在计算 PE 分位点时跳过这些无效值，仅基于有效正值序列计算排名

#### Scenario: 历史数据不足时不捏造

- **WHEN** 传入的历史估值日线有效记录少于 60 个交易日
- **THEN** 快照构建器 SHALL 将对应指标的分位点标记为 N/A，SHALL NOT 基于不足样本强行计算

---

### Requirement: 预计算模型 — PEG 比率

快照构建器 SHALL 计算 PEG 比率：`PEG = PE-TTM / growth_rate_avg`。其中 `growth_rate_avg` 为最近 4 季度利润 YoY 增速的平均值（由财务数据相邻同期记录计算）。

#### Scenario: PEG 正确计算

- **WHEN** 快照构建器收到有效的 PE-TTM 和包含足够期数的财务数据（可计算利润增速）
- **THEN** 输出快照中的 `peg_ratio` SHALL 等于 `PE-TTM / 4 季平均利润增速`，`growth_rate_avg` SHALL 为 4 季平均利润 YoY 增速

#### Scenario: 增速为零或负时 PEG 标记 N/A

- **WHEN** 计算出的 `growth_rate_avg` 为 0 或负值
- **THEN** 快照构建器 SHALL 将 `peg_ratio` 标记为 N/A，SHALL NOT 生成无意义的 PEG 值

#### Scenario: 财务数据不足以计算增速

- **WHEN** 传入的财务数据仅有 1 期（不足以计算 YoY 增速）
- **THEN** 快照构建器 SHALL 将 `growth_rate_avg` 和 `peg_ratio` 均标记为 N/A

---

### Requirement: 预计算模型 — 格雷厄姆数字与安全边际

快照构建器 SHALL 计算格雷厄姆数字（Graham Number）与安全边际（Safety Margin）：
- `Graham Number = sqrt(22.5 × EPS × BPS)`
- `Safety Margin = (Graham Number - Current Price) / Current Price × 100`

#### Scenario: Graham Number 正确计算

- **WHEN** 快照构建器收到有效的 EPS > 0 和 BPS > 0
- **THEN** 输出快照中的 `graham_intrinsic_val` SHALL 等于 `sqrt(22.5 × EPS × BPS)`（保留两位小数）

#### Scenario: EPS 或 BPS 为负/零/None 时标记 N/A

- **WHEN** 财务数据中 EPS ≤ 0 或 BPS ≤ 0 或为 None
- **THEN** 快照构建器 SHALL 将 `graham_intrinsic_val` 和 `graham_safety_margin` 均标记为 N/A，SHALL NOT 抛出异常

#### Scenario: 安全边际正确计算

- **WHEN** Graham Number 为有效数值且 Current Price > 0
- **THEN** `graham_safety_margin` SHALL 等于 `(Graham - Price) / Price × 100`（保留一位小数），正数代表价格低于内在价值

---

### Requirement: 预计算模型 — 毛利率趋势

快照构建器 SHALL 基于多期财务数据计算毛利率同比趋势描述，输出为人类可读字符串（如"同比上升 3.2%"/"同比下降 1.5%"/"持平"）。

#### Scenario: 毛利率趋势正确生成

- **WHEN** 快照构建器收到至少 2 期财务数据且毛利率均有效
- **THEN** 输出快照中的 `gross_margin_trend` SHALL 为描述性字符串，反映最新期与上一期毛利率的变化方向和幅度

#### Scenario: 仅 1 期数据时趋势为 N/A

- **WHEN** 传入的财务数据仅有 1 期
- **THEN** 快照构建器 SHALL 将 `gross_margin_trend` 标记为 N/A

---

### Requirement: 输出契约 — 固定 JSON 结构

估值建模师的产出 SHALL 为固定结构的 JSON（或等价的 DTO），包含：

- `valuation_verdict`（枚举：Undervalued / Fair / Overvalued；契约统一英文，展示层可用 `VERDICT_DISPLAY_LABELS` 映射为中文）
- `confidence_score`（float，0.0–1.0），基于证据一致性打分
- `estimated_intrinsic_value_range`（嵌套对象，含 `lower_bound: str` 和 `upper_bound: str`），基于不同模型推导的价格区间描述
- `key_evidence`（list[str]），须引用输入数据中的具体数值
- `risk_factors`（list[str]）
- `reasoning_summary`（str），专业精炼总结，须明确指出是机会还是陷阱

**解析逻辑 SHALL 内聚到该 Agent**（`agents/valuation_modeler/output_parser.py`）。系统 SHALL 使用 pydantic 或等价机制校验并反序列化本 Agent 的 LLM 输出。若解析失败 SHALL **将 LLM 原始输出写入日志（可截断）** 并抛出领域友好异常（`LLMOutputParseError`），不将未校验的字符串作为估值结果返回给调用方。

#### Scenario: 正常返回符合结构的结果

- **WHEN** LLM 返回合法且可解析的 JSON
- **THEN** Application 层返回的 DTO 包含上述六类字段，且 valuation_verdict 为三值之一、confidence_score 在 [0, 1] 内、key_evidence 和 risk_factors 为非空列表、estimated_intrinsic_value_range 含 lower_bound 和 upper_bound

#### Scenario: LLM 返回非 JSON 或格式错误

- **WHEN** LLM 返回内容无法解析为上述结构的 JSON
- **THEN** 系统 SHALL 将 LLM 原始输出写入日志（可截断）、抛出 `LLMOutputParseError`，不将未校验的字符串作为估值结果返回给调用方

#### Scenario: LLM 返回含 thinking 标签

- **WHEN** LLM 返回内容包含 `<think>...</think>` 标签（reasoning model 的思考过程）
- **THEN** 输出解析器 SHALL 先剥离 thinking 标签再尝试 JSON 解析，不因 thinking 标签导致解析失败

---

### Requirement: 禁止自行计算约束（No Math）

估值建模师的 LLM Prompt SHALL 明确禁止模型自行进行数学运算。所有比率（PEG）、分位点（Percentile）、差值（Safety Margin）均 SHALL 由代码预计算后在 User Prompt 中给出，LLM SHALL 直接引用这些预计算结果。

#### Scenario: 预计算结果在 User Prompt 中呈现

- **WHEN** 估值建模师执行分析流程
- **THEN** 送入 LLM 的 User Prompt SHALL 包含已预计算的 pe_percentile、pb_percentile、ps_percentile、peg_ratio、graham_intrinsic_val、graham_safety_margin 等数值，LLM 不需要也不应该自行计算这些值

---

### Requirement: 证据驱动与无交易建议

估值建模师的观点（key_evidence、risk_factors、reasoning_summary）SHALL 直接引用输入中提供的预计算数据与财务指标读数作为证据（例如「PE 处于历史 5% 分位，极度悲观」「PEG 仅为 0.8，且 ROE 高达 20%」）。估值建模师 SHALL NOT 输出「建议买入」「建议卖出」「立即建仓」等交易指令；该类决策属于 Judge 模块职责。数据标记为 N/A 时，LLM SHALL 明确说明"数据不足"，SHALL NOT 猜测数值。

#### Scenario: 观点引用输入数据

- **WHEN** 输入包含 pe_percentile=5%、peg_ratio=0.8、roe=20% 等数据
- **THEN** key_evidence 与 reasoning_summary 中出现的数值或状态描述 SHALL 与输入一致，不得捏造未提供的读数

#### Scenario: 不输出交易建议

- **WHEN** 估值建模师生成 reasoning_summary
- **THEN** 输出 SHALL NOT 包含建议买入、建议卖出、立即建仓等交易指令类表述

#### Scenario: N/A 数据处理

- **WHEN** 输入中某预计算结果为 N/A（如 PEG 因增速为负标记 N/A）
- **THEN** LLM 输出 SHALL 在相关证据或风险中明确说明"数据不足"或"该模型不适用"，SHALL NOT 用虚构数值替代

---

### Requirement: Prompt 内聚于 Agent 且存放于代码外

估值建模师的 System Prompt 与 User Prompt 模板 SHALL 内聚在该专家（agent）的上下文中，且 SHALL NOT 将 prompt 正文硬编码在代码中。Prompt 内容 SHALL 存放在代码库内约定的资源目录（`src/modules/research/agents/valuation_modeler/prompts/` 下的 `system.md` 与 `user.md`），由该专家的 Infrastructure 在运行时加载；模板中的占位符（如 `{stock_name}`、`{pe_percentile}`、`{peg_ratio}`、`{graham_intrinsic_val}`）SHALL 在代码中用本次调用的估值快照数据填充，使用与财务审计员和技术分析师一致的 Python `str.format()` 风格（`{...}` 单花括号）。

#### Scenario: Prompt 从资源加载

- **WHEN** 估值建模师执行分析流程并需要调用 LLM
- **THEN** 使用的 System Prompt 与 User Prompt 模板来自资源文件（`agents/valuation_modeler/prompts/`），而非 Python 源码中的长字符串

#### Scenario: 占位符由代码填充

- **WHEN** 资源文件中的 User Prompt 包含占位符（如 `{stock_name}`、`{pe_percentile}`、`{peg_ratio}`、`{graham_intrinsic_val}`）
- **THEN** 运行时由代码使用 `str.format()` 和本次调用的估值快照数据填充这些占位符后，再传入 LLM

---

### Requirement: 跨模块与模块内均通过 Port/Application 接口

估值建模师实现 SHALL 仅通过 data_engineering 的 **Application 接口** 获取数据（股票信息：`GetStockBasicInfoUseCase`；历史估值日线：`GetValuationDailiesForTickerUseCase`；财务指标：`GetFinanceForTickerUseCase`）与 llm_platform 的 Application 接口调用 LLM；SHALL NOT 直接依赖上述模块的领域模型、实体、值对象或 Infrastructure 实现。**Research 内部**对「获取估值数据」「构建估值快照」「调用估值 Agent」的依赖 SHALL 通过 Domain Port 进行，Application 层 SHALL NOT 直接依赖 Infrastructure 实现类。入参/出参 SHALL 使用 DTO 或 Port 约定的抽象类型。

#### Scenario: 获取股票信息与市场数据

- **WHEN** 估值建模师需要股票基础信息和最新市场估值数据
- **THEN** 通过 Research 的估值数据 Port（`IValuationDataPort`，其 Adapter 内部调用 data_engineering 的 `GetStockBasicInfoUseCase`）获取 DTO，不直接依赖 data_engineering 的 repository 或 domain 实体

#### Scenario: 获取历史估值日线

- **WHEN** 估值建模师需要历史 PE/PB/PS 时序以计算分位点
- **THEN** 通过 Research 的估值数据 Port（`IValuationDataPort`，其 Adapter 内部调用 data_engineering 的 `GetValuationDailiesForTickerUseCase`）获取 DTO 列表

#### Scenario: 调用 LLM

- **WHEN** 估值建模师需要调用大模型生成估值分析
- **THEN** 通过估值 Agent Port（`IValuationModelerAgentPort`，其实现内部调用 llm_platform 的 Application 接口）传入 system_message 与 prompt，Application 层不直接依赖 llm_platform 的 router、registry 或 adapter 实现类

---

### Requirement: 可测性 — Scenario 与测试一一对应

每个上述 Scenario 在变更交付时 SHALL 对应至少一个自动化测试（单元或集成）；需求完成的验收条件包含「该需求下所有 Scenario 的测试通过」。实现时可采用先实现再补测，不强制测试先行。

#### Scenario: 测试覆盖输入缺失拒绝

- **WHEN** 运行估值建模师相关测试套件
- **THEN** 存在测试用例：传入缺失 symbol 的入参，断言调用被拒绝并返回可区分错误（对应「输入缺失 symbol 时的行为」）

#### Scenario: 测试覆盖标的不存在拒绝

- **WHEN** 运行估值建模师相关测试套件
- **THEN** 存在测试用例：mock 数据 Port 返回 None（标的不存在），断言系统返回明确错误信息

#### Scenario: 测试覆盖无财务数据拒绝

- **WHEN** 运行估值建模师相关测试套件
- **THEN** 存在测试用例：mock 财务数据返回空列表，断言系统返回明确错误信息（对应「该标的无财务数据时的行为」）

#### Scenario: 测试覆盖 LLM 解析失败

- **WHEN** 运行估值建模师相关测试套件
- **THEN** 存在测试用例：mock LLM 返回非 JSON 或非法结构，断言系统抛出 `LLMOutputParseError`、不返回未校验字符串

#### Scenario: 测试覆盖快照构建预计算

- **WHEN** 运行估值建模师相关测试套件
- **THEN** 存在测试用例：传入已知数据，断言快照构建器输出的 pe_percentile、peg_ratio、graham_intrinsic_val、graham_safety_margin 等预计算指标正确（对应分位点、PEG、Graham 各 Scenario）

#### Scenario: 测试覆盖 N/A 边界条件

- **WHEN** 运行估值建模师相关测试套件
- **THEN** 存在测试用例：EPS 为 0 时 Graham 为 N/A；增速为负时 PEG 为 N/A；历史数据不足时分位点为 N/A
