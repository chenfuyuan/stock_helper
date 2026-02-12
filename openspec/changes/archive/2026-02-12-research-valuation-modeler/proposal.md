# Proposal: Research 模块 — 估值建模师

## Why

Research 作为「事实工厂」需要五专家之一 **估值建模师**，负责剥离市场情绪，仅基于基本面数据与预计算估值模型计算标的的「内在价值」与「安全边际」，输出结构化的估值判断。估值建模师不做交易建议，只评估当前价格相对于内在价值是被低估、合理还是高估，为后续 Debate/Judge 提供可引用的估值面证据。核心哲学为 **"怀疑市场情绪，只相信现金流和资产负债表"** —— 观点必须由预计算的估值模型数据支撑，禁止自行计算，禁止捏造数据。

## What Changes

- **新增估值建模师角色**：以「高级估值建模师 (Senior Valuation Modeler)」人设，采用 **四步分析框架**（相对估值 → 成长匹配度 → 价值地板 → 排雷）对标的进行内在价值评估，不做最终交易决策。
- **输入契约**：接受股票代码（symbol）；系统自动从 data_engineering 获取该标的的：
  1. **股票基础信息**（名称、行业）—— 通过 `GetStockBasicInfoUseCase`。
  2. **最新市场数据**（当前价格、市值、PE-TTM、PB、PS-TTM、股息率）—— 通过 `GetStockBasicInfoUseCase` 返回的最新 `StockDaily`。
  3. **历史估值时序数据**（过去 N 个交易日的 PE-TTM、PB、PS-TTM）—— 通过 data_engineering **新增的估值日线查询用例**（见下方前置依赖）。
  4. **财务指标数据**（ROE、毛利率、净利率、资产负债率、EPS、BPS、利润增速等）—— 通过 `GetFinanceForTickerUseCase`（需新增 `bps` 字段）。
  在 Research 内部，由「估值快照构建器」将上述原始数据**预计算**为：历史分位点（PE/PB/PS 的 3 年分位点）、PEG 比率、格雷厄姆数字与安全边际、毛利率趋势等，填充到 User Prompt 模板后送入 LLM。**所有预计算结果在代码中完成，LLM 禁止自行计算。**
- **输出契约**：固定 JSON 结构，包含：`valuation_verdict`（Undervalued / Fair / Overvalued）、`confidence_score`（0.0–1.0）、`estimated_intrinsic_value_range`（lower_bound / upper_bound）、`key_evidence`（证据列表）、`risk_factors`（风险列表）、`reasoning_summary`（专业精炼总结，须解释是机会还是陷阱）。
- **绝对约束**：禁止自行计算（No Math）—— 所有比率/分位点/差值在输入中给出，LLM 直接引用；禁止联网；禁止幻觉（数据缺失标记 N/A）；不输出交易建议。
- **集成方式**：估值建模师作为 Research 内一个独立分析单元，依赖 data_engineering（股票基础信息、市场行情、财务指标）、llm_platform（LLM 调用）的 **Application 接口**。本变更仅暴露估值建模师专属入口（如 `ValuationModelerService`），Coordinator 直接调用该接口。
- **Prompt 归属与存放**：System Prompt 与 User Prompt 模板**内聚在该专家中**，存放在 `agents/valuation_modeler/prompts/`（`system.md` 与 `user.md`），运行时加载，模板占位符在代码中用预计算的估值快照数据填充。Prompt 内容已预先定义（见本变更目录下的 `system.md` 与 `user.md`）。
- **data_engineering 前置依赖**：
  1. 当前 `DailyBarDTO` 仅含 OHLCV，不包含估值字段（pe_ttm、pb、ps_ttm、dv_ratio、total_mv 等），而 `StockDaily` 域模型本身包含这些字段。本变更需在 data_engineering 中**新增估值日线查询用例**（如 `GetValuationDailiesForTickerUseCase`），按标的与日期区间返回含估值字段的 `ValuationDailyDTO` 列表，供 Research 计算历史分位点。
  2. 当前 `FinanceIndicatorDTO` 不包含 `bps`（每股净资产），而 `StockFinance` 域模型有此字段。本变更需在 `FinanceIndicatorDTO` 中**新增 `bps` 字段**，供格雷厄姆数字计算。
- **实现与验证方式**：Spec 中每个 Scenario 在变更完成时须有对应自动化测试；实现顺序灵活，交付以**完整测试通过**为完成标准。

## Capabilities

### New Capabilities

- **`research-valuation-modeler`**：估值建模师能力。定义输入（股票代码 → 系统获取市场估值数据 + 财务指标）、输出（ValuationResult JSON 结构）、四步分析框架（相对估值/PEG/Graham/排雷）、与 LLM 的 Prompt 契约（禁止计算 / 数据驱动 / 输出纯 JSON），以及预计算模型（历史分位点、PEG、格雷厄姆数字、安全边际）的构建规约。每个需求下的 Scenario 在交付时须有对应自动化测试。

### Modified Capabilities

- （无。财务审计员与技术分析师的能力 spec 不受影响；三者为独立专家，各自有独立 Application 接口。）

## Impact

- **代码**：在 `src/modules/research/` 下新增估值建模师相关 Domain（输入/输出 DTO）、Application 服务（编排数据获取 + 预计算 + LLM 调用 + 解析）、Domain Port（`IValuationDataPort`、`IValuationSnapshotBuilder`、`IValuationModelerAgentPort`）及 Infrastructure 适配。新增 `agents/valuation_modeler/` 目录含 Prompt 资源与输出解析器。
- **依赖**：Research 依赖 data_engineering（股票基础信息、估值日线查询、财务指标查询）、llm_platform（LLM 调用）；不依赖 Coordinator/Debate/Judge。需在 data_engineering 中新增估值日线查询 Application 接口（`GetValuationDailiesForTickerUseCase`）及 `FinanceIndicatorDTO` 的 `bps` 字段扩展。
- **API/系统**：估值建模师产出为 ResearchReport 的一个片段。Research 对 Coordinator 按专家暴露独立接口（本变更仅估值建模师一个接口）。若提供 HTTP 接口，响应体 SHALL 与技术分析师/财务审计员一致：包含 input、output、valuation_indicators（代码塞入的估值快照，便于调试与审计追溯）。
- **测试与可验证性**：Spec 中所有 Scenario 在交付时须有对应自动化测试；交付完成以「完整测试通过 + 无跨模块直接依赖」为验收条件。
- **非目标**：本变更不实现 Research 的「并行五专家」编排、不实现 Debate/Judge；不实现其余专家；不改变现有技术分析师与财务审计员的实现。
