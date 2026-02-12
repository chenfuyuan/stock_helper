# Tasks: research-valuation-modeler

实现估值建模师能力。任务按依赖排序；**实现顺序灵活**（可先实现再补测），交付前须完成**完整测试**，使所有 Spec Scenario 有对应通过测试。

---

## 1. data_engineering 扩展（前置依赖）

- [x] 1.1 在 `IMarketQuoteRepository` 中新增读方法 `get_valuation_dailies(third_code: str, start_date: date, end_date: date) -> List[StockDaily]`，返回指定日期区间的日线记录（含估值字段）
- [x] 1.2 在 `pg_quote_repo`（`StockDailyRepositoryImpl`）中实现该查询方法
- [x] 1.3 新增 Application 查询用例 `GetValuationDailiesForTickerUseCase`（入参 ticker + start_date + end_date，出参 `ValuationDailyDTO` 列表），`ValuationDailyDTO` 包含字段：trade_date、close、pe_ttm、pb、ps_ttm、dv_ratio、total_mv；遵循 `GetDailyBarsForTickerUseCase` 的已有模式
- [x] 1.4 在 `FinanceIndicatorDTO` 中新增 `bps: Optional[float] = None` 字段；在 `GetFinanceForTickerUseCase` 的 DTO 转换中映射 `StockFinance.bps → FinanceIndicatorDTO.bps`

## 2. Research Domain — 估值建模师 DTO 与 Ports

- [x] 2.1 在 domain 中新增估值建模师输出 DTO：`ValuationResultDTO`（valuation_verdict、confidence_score、estimated_intrinsic_value_range、key_evidence、risk_factors、reasoning_summary）、`IntrinsicValueRangeDTO`（lower_bound: str、upper_bound: str）、`ValuationModelAgentResult`（result + raw_llm_output + user_prompt）
- [x] 2.2 在 domain/ports/ 中新增估值建模师输入 DTO：`StockOverviewInput`（stock_name、industry、third_code、current_price、total_mv、pe_ttm、pb、ps_ttm、dv_ratio）、`ValuationDailyInput`（trade_date、close、pe_ttm、pb、ps_ttm）、`ValuationSnapshotDTO`（与 User Prompt 模板占位符一一对应：stock_name、stock_code、current_date、industry、current_price、total_mv、pe_ttm、pe_percentile、pb、pb_percentile、ps_ttm、ps_percentile、dv_ratio、roe、gros_profit_margin、gross_margin_trend、net_profit_margin、debt_to_assets、growth_rate_avg、peg_ratio、graham_intrinsic_val、graham_safety_margin）
- [x] 2.3 在 `FinanceRecordInput` 中新增 `bps: Optional[float] = None` 字段（向后兼容）；在 `FinancialDataAdapter._to_finance_record` 映射中添加 `bps` 字段传递
- [x] 2.4 在 domain/ports/ 中定义三个 Port：`IValuationDataPort`（含 get_stock_overview、get_valuation_dailies、get_finance_for_valuation 三个方法）、`IValuationSnapshotBuilder`（build 方法）、`IValuationModelerAgentPort`（analyze 方法）

## 3. 输入契约 — 缺失必填与无数据时拒绝

- [x] 3.1 在 `ValuationModelerService` 入口做入参校验：symbol 必填，缺失或空字符串时抛出 `BadRequestException`
- [x] 3.2 在 Application 编排中校验 `get_stock_overview` 返回结果：若为 None（标的不存在）则抛出明确错误（「该标的不存在」）
- [x] 3.3 在 Application 编排中校验财务数据返回结果：若为空列表则抛出明确错误（「该标的无财务数据，请先同步」）

## 4. 输出契约 — LLM 返回解析

- [x] 4.1 创建 `agents/valuation_modeler/output_parser.py`：将 LLM 返回字符串用 pydantic 反序列化为 `ValuationResultDTO`；支持 ```json 包裹与 `<think>` 标签剥离；非法 JSON 或缺字段时记录日志（含原始输出，可截断）并抛出 `LLMOutputParseError`
- [x] 4.2 实现 valuation_verdict 校验：确保为三值之一（Undervalued (低估) / Fair (合理) / Overvalued (高估)）；confidence_score ∈ [0, 1]；key_evidence 和 risk_factors 为非空列表

## 5. 估值快照构建（Infrastructure）— 预计算

- [x] 5.1 实现 `IValuationSnapshotBuilder` 的 Infrastructure 实现（`valuation_snapshot/snapshot_builder.py`）：将 `StockOverviewInput` + `List[ValuationDailyInput]` + `List[FinanceRecordInput]` 转为 `ValuationSnapshotDTO`
- [x] 5.2 实现历史分位点计算：PE-TTM、PB、PS-TTM 在有效历史序列（跳过 None/负值/0）中的百分位排名（0–100 整数）；有效数据 < 60 条时标记 N/A
- [x] 5.3 实现 PEG 比率计算：PEG = PE-TTM / growth_rate_avg；growth_rate_avg 为最近 4 季度利润 YoY 增速平均值（由财务数据相邻同期计算）；增速 ≤ 0 或数据不足时标记 N/A
- [x] 5.4 实现格雷厄姆数字与安全边际计算：Graham = sqrt(22.5 × EPS × BPS)；Safety Margin = (Graham - Price) / Price × 100；EPS/BPS ≤ 0 或为 None 时标记 N/A
- [x] 5.5 实现毛利率趋势计算：比较最新期与上一期 gross_margin，输出趋势描述字符串；仅 1 期数据时标记 N/A
- [x] 5.6 实现 ROE 取值：使用 `roe_waa` 作为 User Prompt 的 `roe` 字段

## 6. Research Infrastructure — Adapter

- [x] 6.1 实现 `IValuationDataPort` 的 Adapter（`valuation_data_adapter.py`）：
  - `get_stock_overview(symbol)`：内部调用 `GetStockBasicInfoUseCase`，将 StockInfo + StockDaily 转为 `StockOverviewInput`
  - `get_valuation_dailies(ticker, start_date, end_date)`：内部调用 `GetValuationDailiesForTickerUseCase`，将 `ValuationDailyDTO` 转为 `ValuationDailyInput`
  - `get_finance_for_valuation(ticker, limit)`：内部调用 `GetFinanceForTickerUseCase`，将 `FinanceIndicatorDTO` 转为 `FinanceRecordInput`（含 bps）
- [x] 6.2 实现 `IValuationModelerAgentPort` 的 Adapter（`valuation_modeler_agent_adapter.py`）：加载 Prompt → 填充占位符 → 调用已有 `ILLMPort` → 调用 output_parser 解析；Application 不直接依赖 LLMPort 或 prompt 加载实现

## 7. Prompt 资源与加载

- [x] 7.1 将已定义的 system.md 与 user.md 拷贝至 `src/modules/research/agents/valuation_modeler/prompts/`，复用已有 prompt 加载模式
- [x] 7.2 在 `prompt_loader.py` 中新增估值建模师的加载与填充函数：`load_valuation_modeler_system_prompt`、`load_valuation_modeler_user_template`、`fill_valuation_modeler_user_prompt`（使用 `str.format()` 填充 `{...}` 单花括号占位符，与财务审计员和技术分析师一致；共 22 个占位符与 `ValuationSnapshotDTO` 字段一一对应）

## 8. Application 层 — 完整编排

- [x] 8.1 实现 `ValuationModelerService.run(symbol)` 完整编排：校验 symbol → 通过 `IValuationDataPort.get_stock_overview` 获取股票概览（校验非空）→ 通过 `get_valuation_dailies` 获取历史估值日线（默认 3 年）→ 通过 `get_finance_for_valuation` 获取财务数据（校验非空）→ 通过 `IValuationSnapshotBuilder` 构建估值快照 → 通过 `IValuationModelerAgentPort` 调用估值分析 → 组装完整响应（解析结果 + input、valuation_indicators、output）
- [x] 8.2 确保编排中 Application 仅依赖三个 Domain Port，不直接引用 Infrastructure 实现或第三方库

## 9. Presentation 层 — REST 路由

- [x] 9.1 创建 `presentation/rest/valuation_modeler_routes.py`：通过 FastAPI `Depends` 链式装配 `ValuationModelerService` 所需的全部 Port 实现（`IValuationDataPort` → `ValuationDataAdapter`、`IValuationSnapshotBuilder` → `ValuationSnapshotBuilderImpl`、`IValuationModelerAgentPort` → `ValuationModelerAgentAdapter`），与 `financial_auditor_routes.py` 同级同模式
- [x] 9.2 定义 `ValuationModelApiResponse`（Pydantic 响应模型）：包含 valuation_verdict、confidence_score、estimated_intrinsic_value_range、key_evidence、risk_factors、reasoning_summary、input、valuation_indicators、output
- [x] 9.3 实现路由函数 `GET /research/valuation-model`：入参 `symbol`（Query 必填），调用 `ValuationModelerService.run(symbol)`，异常处理（BadRequestException→400、LLMOutputParseError→422、其他→500 并记录日志）
- [x] 9.4 将新路由注册到 FastAPI app（与已有 research 路由同方式挂载）

## 10. 完整测试与验收

- [x] 10.1 为 data_engineering 扩展编写测试：`GetValuationDailiesForTickerUseCase` 给定 ticker + 日期区间返回含估值字段的 DTO 列表；`FinanceIndicatorDTO` 含 bps 字段
- [x] 10.2 为输入校验编写测试：传入缺失 symbol 时断言被拒绝；mock 数据 Port 返回 None（标的不存在）时断言明确错误；mock 财务数据返回空列表时断言明确错误
- [x] 10.3 为输出解析编写测试：合法 JSON 解析后字段正确；非 JSON 或缺字段时解析失败且不返回未校验字符串；含 `<think>` 标签时正确剥离后解析
- [x] 10.4 为估值快照构建编写测试：传入已知数据断言分位点计算正确；PE 为负时跳过；历史数据 < 60 条时分位点为 N/A；PEG 增速为负时为 N/A；EPS 为 0 时 Graham 为 N/A；Graham 正确时安全边际正确；毛利率趋势在多期/单期情况下正确
- [x] 10.5 为 Application 编排编写 E2E mock 测试：mock 三个 Port 返回固定数据，断言完整编排返回结果包含 valuation_verdict、input、valuation_indicators、output 等字段
- [x] 10.6 确认 Research 模块新增的估值建模师代码无对 data_engineering、llm_platform 的 domain 或 infrastructure 的直接引用，仅通过 Application 接口调用
- [x] 10.7 运行全部测试并通过，确保所有 Spec Scenario 有对应覆盖
