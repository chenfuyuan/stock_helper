# Tasks: research-financial-auditor

实现财务审计员能力。任务按依赖排序；**实现顺序灵活**（可先实现再补测），交付前须完成**完整测试**，使所有 Spec Scenario 有对应通过测试。

---

## 1. data_engineering 财务数据查询接口（前置依赖）

- [x] 1.1 在 `IFinancialDataRepository` 中新增读方法 `get_by_third_code_recent(third_code: str, limit: int) -> List[StockFinance]`，按 `end_date` 降序返回最近 N 期记录
- [x] 1.2 在 `pg_finance_repo` 中实现该查询方法
- [x] 1.3 新增 Application 查询用例 `GetFinanceForTickerUseCase`（入参 ticker + limit，出参 `FinanceIndicatorDTO` 列表），遵循 `GetDailyBarsForTickerUseCase` 的已有模式：注入 Repository、查询、转 DTO 返回
- [x] 1.4 为财务数据查询接口编写测试：给定 ticker 与 limit 调用接口，断言返回 DTO 列表且含盈利/效率/偿债/现金流等字段

## 2. Research Domain — 财务审计员 DTO 与 Ports

- [x] 2.1 在 domain 中新增财务审计员输出 DTO：`FinancialAuditResultDTO`（financial_score、signal、confidence、summary_reasoning、dimension_analyses、key_risks、risk_warning）、`DimensionAnalysisDTO`（dimension、score、assessment、key_findings）、`FinancialAuditAgentResult`（result + raw_llm_output + user_prompt）
- [x] 2.2 在 domain 中新增财务审计员输入 DTO：`FinanceRecordInput`（从 data_engineering DTO 转入的 Research 内部财务数据 DTO）、`FinancialSnapshotDTO`（静态快照 + 历史趋势，字段与 User Prompt 模板占位符一一对应）
- [x] 2.3 在 domain/ports/ 中定义三个 Port：`IFinancialDataPort`（获取财务指标数据）、`IFinancialSnapshotBuilder`（构建快照）、`IFinancialAuditorAgentPort`（调用审计 Agent）
- [x] 2.4 为 DTO 校验编写测试：financial_score ∈ [0, 100]、signal 为五值之一、confidence ∈ [0, 1]、dimension_analyses 含 5 个维度

## 3. 输入契约 — 缺失必填与无数据时拒绝

- [x] 3.1 在 `FinancialAuditorService` 入口做入参校验：symbol 必填，缺失或空字符串时抛出 `BadRequestException`
- [x] 3.2 在 Application 编排中校验财务数据返回结果：若为空列表则抛出明确错误（「该标的无财务数据，请先同步」）
- [x] 3.3 编写测试：传入缺失 symbol 时断言被拒绝；mock 财务数据 Port 返回空列表时断言返回明确错误信息

## 4. 输出契约 — LLM 返回解析

- [x] 4.1 创建 `agents/financial_auditor/output_parser.py`：将 LLM 返回字符串用 pydantic 反序列化为 `FinancialAuditResultDTO`；支持 ```json 包裹；非法 JSON 或缺字段时记录日志（含原始输出，可截断）并抛出 `LLMOutputParseError`
- [x] 4.2 实现 financial_score → signal 一致性校验：若 LLM 返回的 score 与 signal 不匹配评分区间映射，以 score 为准重新映射 signal
- [x] 4.3 编写测试：合法 JSON 解析后字段正确；非 JSON 或缺字段时解析失败且不返回未校验字符串；score/signal 不匹配时自动修正

## 5. 财务快照构建（Infrastructure）

- [x] 5.1 实现 `IFinancialSnapshotBuilder` 的 Infrastructure 实现：将多期 `FinanceRecordInput` 转为 `FinancialSnapshotDTO`（按 end_date 降序、提取静态快照、构建历史趋势序列）
- [x] 5.2 实现派生指标计算：quality_ratio = OCFPS / EPS（EPS 为 0 时标记 N/A）、由 end_date 推算季度标签（如 "2024Q3"）
- [x] 5.3 实现 YoY 增速计算：基于相邻同期记录计算 revenue_growth_yoy、profit_growth_yoy；数据不足时标记 N/A
- [x] 5.4 编写测试：传入已知多期数据断言快照各字段正确；EPS 为 0 时 quality_ratio 为 N/A；仅 1 期数据时 YoY 为 N/A

## 6. Research Infrastructure — Adapter

- [x] 6.1 实现 `IFinancialDataPort` 的 Adapter（`financial_data_adapter.py`）：内部调用 data_engineering 的 `GetFinanceForTickerUseCase`，将 `FinanceIndicatorDTO` 转为 Research 的 `FinanceRecordInput`，不直接依赖 data_engineering 的 repository/domain
- [x] 6.2 实现 `IFinancialAuditorAgentPort` 的 Adapter（`financial_auditor_agent_adapter.py`）：加载 Prompt → 填充占位符 → 调用已有 `ILLMPort` → 调用 output_parser 解析；Application 不直接依赖 LLMPort 或 prompt 加载实现

## 7. Prompt 资源与加载

- [x] 7.1 将已定义的 system.md 与 user.md 拷贝至 `src/modules/research/agents/financial_auditor/prompts/`，复用已有 `prompt_loader` 加载
- [x] 7.2 在 Agent Adapter 中实现占位符填充：用 `FinancialSnapshotDTO` 各字段填充 User Prompt 模板中的 `{symbol}`、`{report_period}`、`{gross_margin}`、`{roic_series}` 等占位符

## 8. Application 层 — 完整编排

- [x] 8.1 实现 `FinancialAuditorService.run(symbol)` 完整编排：校验 symbol → 通过 `IFinancialDataPort` 获取多期财务数据 → 校验非空 → 通过 `IFinancialSnapshotBuilder` 构建快照 → 通过 `IFinancialAuditorAgentPort` 调用审计分析 → 组装完整响应（解析结果 + input、financial_indicators、output，与技术分析师 technical_indicators 对应）
- [x] 8.2 确保编排中 Application 仅依赖三个 Domain Port，不直接引用 Infrastructure 实现或第三方库

## 9. 完整测试与验收

- [x] 9.1 为所有 Spec Scenario 补全/编写对应测试（输入校验、无数据拒绝、输出解析、score/signal 一致性、快照构建、Adapter 调用、Prompt 加载与填充、E2E mock 编排等），运行全部测试并通过
- [x] 9.2 确认 Research 模块新增的财务审计员代码无对 data_engineering、llm_platform 的 domain 或 infrastructure 的直接引用，仅通过 Application 接口调用
- [x] 9.3 响应体含 input、output、financial_indicators：E2E 测试断言 Application 返回结果包含上述字段（对应 HTTP 响应体 Requirement）
