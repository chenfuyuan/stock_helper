# Tasks: research-technical-analyst

实现技术分析师能力。任务按依赖排序；**实现顺序灵活**（可先实现再补测），交付前须完成**完整测试**，使所有 Spec Scenario 有对应通过测试。

---

## 1. data_engineering 日线查询接口（前置依赖）

- [x] 1.1 在 data_engineering 中新增只读查询用例 GetDailyBarsForTicker（入参 ticker、日期区间，出参日线 DTO 列表），通过 Application 层暴露；与现有 domain/model 对齐
- [x] 1.2 为日线查询接口编写测试：给定 ticker 与日期区间调用接口，断言返回 DTO 列表且含开高低收量等字段

## 2. Research 模块骨架与 Domain / Ports / Application 入口

- [x] 2.1 创建 `src/modules/research/` 及四层目录；在 domain 中定义 TechnicalAnalysisResultDTO、KeyTechnicalLevelsDTO 及输入 DTO（DailyBarInput 等）
- [x] 2.2 定义 Research 依赖的 Port（IMarketQuotePort、ILLMPort）；实现最小 TechnicalAnalystService（入参 ticker、analysis_date，出参 TechnicalAnalysisResultDTO），依赖 Port 注入
- [x] 2.3 为 DTO 校验与 Application 接口编写测试（signal/confidence 校验、入参出参为 DTO）

## 3. 输入契约 — 缺失必填时拒绝

- [x] 3.1 在 Application 入口做入参校验：ticker、analysis_date 必填，缺失时抛出 BadRequestException
- [x] 3.2 编写测试：传入缺失 ticker 或 analysis_date 时断言被拒绝并返回可区分错误

## 4. 输出契约 — LLM 返回解析

- [x] 4.1 在 Application 或 Domain 层实现：将 LLM 返回的字符串用 pydantic 反序列化为 TechnicalAnalysisResultDTO；非法 JSON 或缺字段时记录日志并抛出/返回明确错误
- [x] 4.2 编写测试：合法 JSON 解析后字段正确、signal 为三值之一、confidence ∈ [0,1]；非 JSON 或缺字段时解析失败且不返回未校验字符串

## 5. Research Infrastructure — Adapter 与指标计算

- [x] 5.1 实现获取日线 Port 的 Adapter：内部调用 data_engineering 的 GetDailyBarsForTicker Application 接口，不直接依赖其 repository/domain
- [x] 5.2 实现调用 LLM 的 Port 的 Adapter：内部调用 llm_platform 的 LLMService.generate，不直接依赖 router/registry
- [x] 5.3 实现 Research 内指标计算（基于日线计算 RSI、MA、MACD、KDJ、ADX、OBV 及简单支撑/阻力），输出与 spec 输入契约一致

## 6. Prompt 资源与加载

- [x] 6.1 创建技术分析师 Prompt 资源目录（如 `agents/technical_analyst/prompts/`），放入 system.md、user.md；实现运行时加载（读文件或 Port）
- [x] 6.2 在调用 LLM 前用本次输入的指标与资产信息填充模板占位符

## 7. Application 层 — 完整编排

- [x] 7.1 实现 TechnicalAnalystService 完整编排：通过 Port 获取日线 → 指标计算 → 加载并填充 Prompt → 通过 Port 调用 LLM → 解析为 TechnicalAnalysisResultDTO；解析失败时按 4.1 处理

## 8. 完整测试与验收

- [x] 8.1 为所有 Spec Scenario 补全/编写对应测试（输出解析、Adapter 调用、Prompt 加载、占位符填充、E2E mock 编排等），运行全部测试并通过
- [x] 8.2 确认 Research 模块无对 data_engineering、llm_platform 的 domain 或 infrastructure 的直接引用，仅通过 Application 接口调用
