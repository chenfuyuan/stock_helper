# Tasks: research-catalyst-detective

实现催化剂侦探能力。任务按依赖排序；**实现顺序灵活**（可先实现再补测），交付前须完成**完整测试**，使所有 Spec Scenario 有对应通过测试。**无需上游模块变更**（`LLMPlatformContainer.web_search_service()` 已在宏观情报员变更中就绪）。

---

## 1. Research Domain — 催化剂侦探 DTO

- [x] 1.1 新增 `domain/dtos/catalyst_inputs.py`：`CatalystStockOverview`（stock_name、industry、third_code）、`CatalystSearchResultItem`（title、url、snippet、summary: Optional、site_name: Optional、published_date: Optional）、`CatalystSearchResult`（dimension_topic: str、items: List[CatalystSearchResultItem]）
- [x] 1.2 新增 `domain/dtos/catalyst_context.py`：`CatalystContextDTO`（9 个字段与 user.md 占位符一一对应：stock_name、third_code、industry、current_date、company_events_context、industry_catalyst_context、market_sentiment_context、earnings_context、all_source_urls）
- [x] 1.3 新增 `domain/dtos/catalyst_dtos.py`：`CatalystEvent`（event、expected_impact、timeframe、probability）、`CatalystDimensionAnalysis`（dimension、assessment、score: int 0-100、key_findings: list[str]）、`CatalystDetectiveResultDTO`（catalyst_assessment: Literal 三值、confidence_score: float 0-1、catalyst_summary、dimension_analyses: list[CatalystDimensionAnalysis] 4 项、positive_catalysts: list[CatalystEvent]、negative_catalysts: list[CatalystEvent]、information_sources: list[str]）、`CatalystDetectiveAgentResult`（result + raw_llm_output + user_prompt）

## 2. Research Domain — 催化剂侦探 Ports

- [x] 2.1 新增 `domain/ports/catalyst_data.py`：`ICatalystDataPort`（含 `get_stock_overview(symbol) -> Optional[CatalystStockOverview]` 与 `search_catalyst_context(stock_name, industry) -> List[CatalystSearchResult]` 两个方法）
- [x] 2.2 新增 `domain/ports/catalyst_context_builder.py`：`ICatalystContextBuilder`（`build(overview: CatalystStockOverview, search_results: List[CatalystSearchResult]) -> CatalystContextDTO`）
- [x] 2.3 新增 `domain/ports/catalyst_detective_agent.py`：`ICatalystDetectiveAgentPort`（`analyze(symbol: str, catalyst_context: CatalystContextDTO) -> CatalystDetectiveAgentResult`）

## 3. 催化剂上下文构建（Infrastructure）

- [x] 3.1 实现 `ICatalystContextBuilder` 的 Infrastructure 实现（`infrastructure/catalyst_context/context_builder.py`：`CatalystContextBuilderImpl`）：入参 `CatalystStockOverview` + `List[CatalystSearchResult]`，出参 `CatalystContextDTO`
- [x] 3.2 实现按维度归类：将搜索结果按 `dimension_topic` 归类，每个维度的条目格式化为文本段落（标题 + 来源 + 日期 + 摘要内容）
- [x] 3.3 实现来源 URL 收集：从全部搜索结果中提取去重 URL 列表，格式化为 `all_source_urls` 字符串
- [x] 3.4 实现空结果处理：某维度搜索返回 0 条结果时，该维度上下文标记为"该维度暂无搜索结果，信息有限"
- [x] 3.5 填充 `current_date`（`date.today()` 格式化）、`stock_name`、`third_code`、`industry`（从 `CatalystStockOverview` 透传）

## 4. Research Infrastructure — Adapter

- [x] 4.1 实现 `ICatalystDataPort` 的 Adapter（`infrastructure/adapters/catalyst_data_adapter.py`：`CatalystDataAdapter`）：
  - `get_stock_overview(symbol)`：内部调用 data_engineering 的 `GetStockBasicInfoUseCase`，提取 stock_name、industry、third_code 转为 `CatalystStockOverview`；标的不存在时返回 None
  - `search_catalyst_context(stock_name, industry)`：内部调用 llm_platform 的 `WebSearchService`，按四个维度构建搜索查询（公司事件、行业催化、市场情绪、业绩预期），每个维度使用 `freshness="oneMonth"`、`count=8`、`summary=True`
- [x] 4.2 实现搜索查询动态生成：根据 `stock_name`、`industry` 和 `当前年份` 填充查询模板；**所有查询以公司名称开头**以聚焦个股级催化事件；四次搜索顺序执行
- [x] 4.3 实现单维度搜索异常优雅降级：每维度搜索独立 try/except，失败时记录警告日志，返回空结果的 `CatalystSearchResult(dimension_topic=..., items=[])`，不中断其他维度搜索
- [x] 4.4 实现 `ICatalystDetectiveAgentPort` 的 Adapter（`infrastructure/adapters/catalyst_detective_agent_adapter.py`：`CatalystDetectiveAgentAdapter`）：加载 Prompt → 填充占位符 → 调用已有 `ILLMPort` → 调用 output_parser 解析；Application 不直接依赖 LLMPort 或 prompt 加载实现

## 5. 输出契约 — LLM 返回解析

- [x] 5.1 创建 `infrastructure/agents/catalyst_detective/output_parser.py`：将 LLM 返回字符串用 pydantic 反序列化为 `CatalystDetectiveResultDTO`；支持 markdown 代码块剥离与 `<think>` 标签剥离（复用 `_strip_thinking_tags`）；非法 JSON 或缺字段时记录日志（含原始输出，可截断）并抛出 `LLMOutputParseError`
- [x] 5.2 实现 catalyst_assessment 校验：确保为三值之一（Positive (正面催化) / Neutral (中性) / Negative (负面催化)）；confidence_score ∈ [0, 1]；dimension_analyses 包含 4 个维度；positive_catalysts 和 negative_catalysts 为非空列表且每项包含 event/expected_impact/timeframe/probability；information_sources 包含至少一个 URL

## 6. Prompt 资源与加载

- [x] 6.1 将已定义的 system.md 与 user.md 拷贝至 `src/modules/research/infrastructure/agents/catalyst_detective/prompts/`
- [x] 6.2 在 `prompt_loader.py` 中新增催化剂侦探的加载与填充函数（使用 `str.format()` 填充 `{...}` 单花括号占位符；共 9 个占位符与 `CatalystContextDTO` 字段一一对应）

## 7. Application 层 — 完整编排

- [x] 7.1 实现 `CatalystDetectiveService.run(symbol)` 完整编排：校验 symbol → 通过 `ICatalystDataPort.get_stock_overview` 获取股票概览（校验非空，None 则抛出「该标的不存在」）→ 通过 `ICatalystDataPort.search_catalyst_context` 执行四维度催化剂搜索 → 校验搜索结果非全空（全部为空时抛出「催化剂搜索全部失败」）→ 通过 `ICatalystContextBuilder.build` 构建催化剂上下文 → 通过 `ICatalystDetectiveAgentPort.analyze` 调用催化剂分析 → 组装完整响应（解析结果 + input、catalyst_indicators、output）
- [x] 7.2 确保编排中 Application 仅依赖三个 Domain Port，不直接引用 Infrastructure 实现或第三方库

## 8. Presentation 层 — REST 路由

- [x] 8.1 创建 `presentation/rest/catalyst_detective_routes.py`：通过 FastAPI `Depends` 装配 `CatalystDetectiveService` 所需的全部 Port 实现（`ICatalystDataPort` → `CatalystDataAdapter`、`ICatalystContextBuilder` → `CatalystContextBuilderImpl`、`ICatalystDetectiveAgentPort` → `CatalystDetectiveAgentAdapter`），与 `macro_intelligence_routes.py` 同级同模式
- [x] 8.2 定义 `CatalystDetectiveApiResponse`（Pydantic 响应模型）：包含 catalyst_assessment、confidence_score、catalyst_summary、dimension_analyses、positive_catalysts、negative_catalysts、information_sources、input、catalyst_indicators、output
- [x] 8.3 实现路由函数 `GET /api/v1/research/catalyst-detective`：入参 `symbol`（Query 必填），调用 `CatalystDetectiveService.run(symbol)`，异常处理（BadRequestException→400、LLMOutputParseError→422、其他→500 并记录日志）
- [x] 8.4 在 `ResearchContainer` 中新增 `catalyst_detective_service()` 工厂方法：装配 `CatalystDataAdapter`（注入 `GetStockBasicInfoUseCase` + `WebSearchService`）、`CatalystContextBuilderImpl`、`LLMAdapter`、`CatalystDetectiveAgentAdapter`，组装 `CatalystDetectiveService`
- [x] 8.5 将新路由注册到 FastAPI app（与已有 research 路由同方式挂载）

## 9. 完整测试与验收

- [x] 9.1 为上下文构建编写测试：传入已知搜索结果，断言各维度文本正确归类；来源 URL 已去重收集；空维度已标记为"信息有限"；`current_date` 正确填充
- [x] 9.2 为输入校验编写测试：传入缺失 symbol 时断言被拒绝；mock 数据 Port 返回 None（标的不存在）时断言明确错误
- [x] 9.3 为搜索降级编写测试：mock 部分维度搜索失败、部分成功，断言系统正常继续分析且失败维度被标记为"信息有限"；mock 全部搜索失败（0 条结果），断言系统抛出明确错误
- [x] 9.4 为输出解析编写测试：合法 JSON 解析后字段正确（包括 CatalystEvent 嵌套结构）；非 JSON 或缺字段时解析失败且不返回未校验字符串；含 `<think>` 标签时正确剥离后解析
- [x] 9.5 为 Application 编排编写 E2E mock 测试：mock 三个 Port 返回固定数据，断言完整编排返回结果包含 catalyst_assessment、input、catalyst_indicators、output 等字段
- [x] 9.6 确认 Research 模块新增的催化剂侦探代码无对 data_engineering、llm_platform 的 domain 或 infrastructure 的直接引用（Port Adapter 中的跨模块调用除外），仅通过 Application 接口调用
- [x] 9.7 运行全部测试并通过，确保所有 Spec Scenario 有对应覆盖
