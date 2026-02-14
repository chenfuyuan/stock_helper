## Why

宏观情报员和催化剂侦探在执行外部搜索（软情报获取）时，产出的 ResearchReport 置信度不足。根因分析：

1. **搜索查询关键词堆砌**：当前每个维度的搜索查询塞入 5-6 个关键词（如 `"{stock_name} 重大事件 并购重组 管理层变动 战略合作 {year}年"`），导致搜索引擎无法精确匹配，返回泛化、低相关性的结果。
2. **搜索参数一刀切**：所有维度统一使用 `count=8`、`freshness="oneMonth"`，未根据维度特性差异化——例如货币政策类信息变化周期较长，而公司重大事件时效性更强。
3. **搜索结果无后处理**：获取的搜索结果全量灌入上下文，无相关性过滤、重复内容去除或噪音剔除（广告页、无关内容），直接拉低了 LLM 分析的信噪比和置信度。

这三个问题叠加，使得两个依赖软情报的专家角色在证据质量上存在系统性缺陷，需要从搜索策略层面进行优化。

## What Changes

- **优化搜索查询构造策略**：将关键词堆砌式查询拆分为聚焦、自然语言风格的精准查询；每个维度使用 2-3 个核心关键词而非 5-6 个，提升搜索引擎的匹配精度。
- **引入维度级搜索参数配置**：为每个搜索维度定义独立的 `count` 和 `freshness` 参数，根据维度信息特性差异化配置（如公司事件类用 `oneWeek` + 较多条数，宏观经济类用 `oneMonth` + 较少条数）。
- **新增搜索结果过滤机制**：在搜索结果进入上下文构建器之前，增加结果过滤层——基于标题/摘要与搜索意图的相关性判断，剔除无关内容（广告、无摘要条目、重复 URL），保留高质量结果。
- **优化上下文构建器的结果排序**：将过滤后的结果按相关性和时效性排序，确保 LLM 优先看到最有价值的信息。

## Capabilities

### New Capabilities

- `research-search-quality`: 研究模块搜索质量优化策略——定义搜索查询构造规范（聚焦查询、关键词精简）、搜索结果过滤规则（相关性过滤、去重、去噪）、以及维度级搜索参数配置标准。作为宏观情报员和催化剂侦探共享的搜索质量基线。

### Modified Capabilities

- `research-macro-intelligence`: 搜索策略要求细化——查询构造须符合 `research-search-quality` 定义的聚焦查询规范；搜索结果须经过滤后再送入上下文构建器。
- `research-catalyst-detective`: 搜索策略要求细化——查询构造须符合 `research-search-quality` 定义的聚焦查询规范；搜索结果须经过滤后再送入上下文构建器。

## Impact

- **受影响代码**：
  - `src/modules/research/infrastructure/adapters/macro_data_adapter.py` — 重构查询模板与搜索参数
  - `src/modules/research/infrastructure/adapters/catalyst_data_adapter.py` — 重构查询模板与搜索参数
  - `src/modules/research/infrastructure/macro_context/context_builder.py` — 可能增加结果排序逻辑
  - `src/modules/research/infrastructure/catalyst_context/context_builder.py` — 可能增加结果排序逻辑
  - 新增搜索结果过滤相关的 Domain Port / DTO 和 Infrastructure 实现
- **受影响 API**：无 API 契约变更（输入输出不变），仅内部搜索策略优化
- **依赖**：无新增外部依赖；继续使用 `llm_platform` 的 `WebSearchService`（搜索 DTO 不变）
- **验证方式**：通过自动化测试验证——查询构造测试（断言关键词数量与格式）、结果过滤测试（断言噪音被剔除）、端到端集成测试（mock 搜索返回含噪数据，断言过滤后上下文质量）
