# Tasks: research-macro-intelligence

实现宏观情报员能力。任务按依赖排序；**实现顺序灵活**（可先实现再补测），交付前须完成**完整测试**，使所有 Spec Scenario 有对应通过测试。

---

## 1. LLMPlatformContainer 扩展（前置依赖）

- [x] 1.1 在 `LLMPlatformContainer` 中新增 `web_search_service()` 工厂方法：内部构造 `BochaWebSearchAdapter`（从 `llm_config` 读取 api_key 和 base_url）并返回 `WebSearchService` 实例；遵循 `llm_service()` 的已有模式

## 2. Research Domain — 宏观情报员 DTO

- [x] 2.1 新增 `domain/dtos/macro_inputs.py`：`MacroStockOverview`（stock_name、industry、third_code）、`MacroSearchResultItem`（title、url、snippet、summary: Optional、site_name: Optional、published_date: Optional）、`MacroSearchResult`（dimension_topic: str、items: List[MacroSearchResultItem]）
- [x] 2.2 新增 `domain/dtos/macro_context.py`：`MacroContextDTO`（9 个字段与 user.md 占位符一一对应：stock_name、third_code、industry、current_date、monetary_context、policy_context、economic_context、industry_context、all_source_urls）
- [x] 2.3 新增 `domain/dtos/macro_dtos.py`：`MacroDimensionAnalysis`（dimension、assessment、score: int 0-100、key_findings: list[str]）、`MacroIntelligenceResultDTO`（macro_environment: Literal 三值、confidence_score: float 0-1、macro_summary、dimension_analyses: list[MacroDimensionAnalysis] 4 项、key_opportunities: list[str]、key_risks: list[str]、information_sources: list[str]）、`MacroIntelligenceAgentResult`（result + raw_llm_output + user_prompt）

## 3. Research Domain — 宏观情报员 Ports

- [x] 3.1 新增 `domain/ports/macro_data.py`：`IMacroDataPort`（含 `get_stock_overview(symbol) -> Optional[MacroStockOverview]` 与 `search_macro_context(industry, stock_name) -> List[MacroSearchResult]` 两个方法）
- [x] 3.2 新增 `domain/ports/macro_context_builder.py`：`IMacroContextBuilder`（`build(overview: MacroStockOverview, search_results: List[MacroSearchResult]) -> MacroContextDTO`）
- [x] 3.3 新增 `domain/ports/macro_intelligence_agent.py`：`IMacroIntelligenceAgentPort`（`analyze(symbol: str, macro_context: MacroContextDTO) -> MacroIntelligenceAgentResult`）

## 4. 宏观上下文构建（Infrastructure）

- [x] 4.1 实现 `IMacroContextBuilder` 的 Infrastructure 实现（`infrastructure/macro_context/context_builder.py`：`MacroContextBuilderImpl`）：入参 `MacroStockOverview` + `List[MacroSearchResult]`，出参 `MacroContextDTO`
- [x] 4.2 实现按维度归类：将搜索结果按 `dimension_topic` 归类，每个维度的条目格式化为文本段落（标题 + 来源 + 日期 + 摘要内容）
- [x] 4.3 实现来源 URL 收集：从全部搜索结果中提取去重 URL 列表，格式化为 `all_source_urls` 字符串
- [x] 4.4 实现空结果处理：某维度搜索返回 0 条结果时，该维度上下文标记为"该维度暂无搜索结果，信息有限"
- [x] 4.5 填充 `current_date`（`date.today()` 格式化）、`stock_name`、`third_code`、`industry`（从 `MacroStockOverview` 透传）

## 5. Research Infrastructure — Adapter

- [x] 5.1 实现 `IMacroDataPort` 的 Adapter（`infrastructure/adapters/macro_data_adapter.py`：`MacroDataAdapter`）：
  - `get_stock_overview(symbol)`：内部调用 data_engineering 的 `GetStockBasicInfoUseCase`，提取 stock_name、industry、third_code 转为 `MacroStockOverview`；标的不存在时返回 None
  - `search_macro_context(industry, stock_name)`：内部调用 llm_platform 的 `WebSearchService`，按四个维度构建搜索查询（货币政策、产业政策、宏观经济、行业景气），每个维度使用 `freshness="oneMonth"`、`count=8`、`summary=True`
- [x] 5.2 实现搜索查询动态生成：根据 `industry` 和 `当前年份` 填充查询模板；四次搜索顺序执行
- [x] 5.3 实现单维度搜索异常优雅降级：每维度搜索独立 try/except，失败时记录警告日志，返回空结果的 `MacroSearchResult(dimension_topic=..., items=[])`，不中断其他维度搜索
- [x] 5.4 实现 `IMacroIntelligenceAgentPort` 的 Adapter（`infrastructure/adapters/macro_intelligence_agent_adapter.py`：`MacroIntelligenceAgentAdapter`）：加载 Prompt → 填充占位符 → 调用已有 `ILLMPort` → 调用 output_parser 解析；Application 不直接依赖 LLMPort 或 prompt 加载实现

## 6. 输出契约 — LLM 返回解析

- [x] 6.1 创建 `infrastructure/agents/macro_intelligence/output_parser.py`：将 LLM 返回字符串用 pydantic 反序列化为 `MacroIntelligenceResultDTO`；支持 markdown 代码块剥离与 `<think>` 标签剥离（复用 `_strip_thinking_tags`）；非法 JSON 或缺字段时记录日志（含原始输出，可截断）并抛出 `LLMOutputParseError`
- [x] 6.2 实现 macro_environment 校验：确保为三值之一（Favorable (有利) / Neutral (中性) / Unfavorable (不利)）；confidence_score ∈ [0, 1]；dimension_analyses 包含 4 个维度；key_opportunities 和 key_risks 为非空列表；information_sources 包含至少一个 URL

## 7. Prompt 资源与加载

- [x] 7.1 将已定义的 system.md 与 user.md 拷贝至 `src/modules/research/infrastructure/agents/macro_intelligence/prompts/`
- [x] 7.2 在 `prompt_loader.py` 中新增宏观情报员的加载与填充函数（使用 `str.format()` 填充 `{...}` 单花括号占位符；共 9 个占位符与 `MacroContextDTO` 字段一一对应）

## 8. Application 层 — 完整编排

- [x] 8.1 实现 `MacroIntelligenceService.run(symbol)` 完整编排：校验 symbol → 通过 `IMacroDataPort.get_stock_overview` 获取股票概览（校验非空，None 则抛出「该标的不存在」）→ 通过 `IMacroDataPort.search_macro_context` 执行四维度宏观搜索 → 校验搜索结果非全空（全部为空时抛出「宏观搜索全部失败」）→ 通过 `IMacroContextBuilder.build` 构建宏观上下文 → 通过 `IMacroIntelligenceAgentPort.analyze` 调用宏观分析 → 组装完整响应（解析结果 + input、macro_indicators、output）
- [x] 8.2 确保编排中 Application 仅依赖三个 Domain Port，不直接引用 Infrastructure 实现或第三方库

## 9. Presentation 层 — REST 路由

- [x] 9.1 创建 `presentation/rest/macro_intelligence_routes.py`：通过 FastAPI `Depends` 装配 `MacroIntelligenceService` 所需的全部 Port 实现（`IMacroDataPort` → `MacroDataAdapter`、`IMacroContextBuilder` → `MacroContextBuilderImpl`、`IMacroIntelligenceAgentPort` → `MacroIntelligenceAgentAdapter`），与 `financial_auditor_routes.py` 同级同模式
- [x] 9.2 定义 `MacroIntelligenceApiResponse`（Pydantic 响应模型）：包含 macro_environment、confidence_score、macro_summary、dimension_analyses、key_opportunities、key_risks、information_sources、input、macro_indicators、output
- [x] 9.3 实现路由函数 `GET /api/v1/research/macro-intelligence`：入参 `symbol`（Query 必填），调用 `MacroIntelligenceService.run(symbol)`，异常处理（BadRequestException→400、LLMOutputParseError→422、其他→500 并记录日志）
- [x] 9.4 在 `ResearchContainer` 中新增 `macro_intelligence_service()` 工厂方法：装配 `MacroDataAdapter`（注入 `GetStockBasicInfoUseCase` + `WebSearchService`）、`MacroContextBuilderImpl`、`LLMAdapter`、`MacroIntelligenceAgentAdapter`，组装 `MacroIntelligenceService`
- [x] 9.5 将新路由注册到 FastAPI app（与已有 research 路由同方式挂载）

## 10. 完整测试与验收

- [ ] 10.1 为上下文构建编写测试：传入已知搜索结果，断言各维度文本正确归类；来源 URL 已去重收集；空维度已标记为"信息有限"；`current_date` 正确填充
- [ ] 10.2 为输入校验编写测试：传入缺失 symbol 时断言被拒绝；mock 数据 Port 返回 None（标的不存在）时断言明确错误
- [ ] 10.3 为搜索降级编写测试：mock 部分维度搜索失败、部分成功，断言系统正常继续分析且失败维度被标记为"信息有限"；mock 全部搜索失败（0 条结果），断言系统抛出明确错误
- [ ] 10.4 为输出解析编写测试：合法 JSON 解析后字段正确；非 JSON 或缺字段时解析失败且不返回未校验字符串；含 `<think>` 标签时正确剥离后解析
- [ ] 10.5 为 Application 编排编写 E2E mock 测试：mock 三个 Port 返回固定数据，断言完整编排返回结果包含 macro_environment、input、macro_indicators、output 等字段
- [ ] 10.6 确认 Research 模块新增的宏观情报员代码无对 data_engineering、llm_platform 的 domain 或 infrastructure 的直接引用（Port Adapter 中的跨模块调用除外），仅通过 Application 接口调用
- [ ] 10.7 运行全部测试并通过，确保所有 Spec Scenario 有对应覆盖
