## Context

Research 模块的宏观情报员（`MacroIntelligenceService`）和催化剂侦探（`CatalystDetectiveService`）是五专家中仅有的两个以**软情报（Web 搜索）**为主要数据源的角色。当前两者的搜索策略存在三个系统性问题：

1. **查询构造**：`MacroDataAdapter` 和 `CatalystDataAdapter` 中的搜索查询模板采用关键词堆砌方式（每条 5-6 个关键词），搜索引擎无法精确匹配，返回泛化结果。
2. **参数配置**：所有维度统一 `count=8`、`freshness="oneMonth"`，未根据维度特性差异化。
3. **结果质量**：搜索结果全量灌入上下文构建器，无过滤、去重、排序。

两个专家的搜索-分析流程完全对称：`DataAdapter（查询+搜索）→ ContextBuilder（格式化）→ AgentAdapter（LLM 分析）`。优化点集中在 DataAdapter 层（查询构造 + 结果过滤）和 ContextBuilder 层（排序）。

**约束**：
- 不引入额外 LLM 调用（不使用 LLM 辅助查询生成或结果打分）
- 不增加搜索 API 调用次数（维持每专家 4 次搜索）
- 不修改 `llm_platform` 的 `WebSearchService` / `WebSearchRequest` / `WebSearchResponse` 接口
- 不修改两个专家的 Application 层编排和输出契约

## Goals / Non-Goals

**Goals:**

1. 提升搜索结果的精准度和相关性——通过聚焦查询降低噪音
2. 提升上下文信噪比——通过规则过滤剔除低质量结果
3. 按维度特性差异化搜索参数——使搜索行为与信息时效性匹配
4. 保留扩展点——过滤器可被 LLM 打分实现替换，无需改动 Adapter 编排

**Non-Goals:**

- 不引入 LLM 辅助搜索（Query Rewriting / Result Scoring）——当前阶段优先验证简单策略的效果
- 不引入多轮搜索（Iterative Refinement）——避免延迟和成本翻倍
- 不增加搜索维度数量——维持每专家 4 维度
- 不修改搜索 API 契约或 `llm_platform` 模块代码

## Decisions

### Decision 1: 搜索维度配置数据化

**选择**：将每个维度的搜索配置（topic、query_template、count、freshness）从 Adapter 方法内的 inline dict 提取为结构化的 `SearchDimensionConfig` 数据类，定义在 `domain/dtos/` 中。

**理由**：
- 当前查询模板、count、freshness 散布在 Adapter 方法的 for 循环中，调优需改代码逻辑
- 数据化后可独立测试配置合理性（如断言关键词数量），且调优只需改配置值
- 两个 Adapter 共享相同的配置结构，提高一致性

**替代方案**：
- 外部化为 YAML/JSON 配置文件 → 过度工程，当前仅 8 个维度（2 专家 × 4 维度），不需要运行时热加载
- 保持 inline dict → 无法独立测试配置，调优不透明

### Decision 2: 聚焦查询——每条查询最多 3 个核心领域关键词

**选择**：将关键词堆砌式查询重构为聚焦查询，每条查询最多包含 **3 个核心领域关键词**（不计 stock_name/industry/year 等上下文词）。

**理由**：
- 搜索引擎对短而精的查询匹配效果远优于长尾关键词堆砌
- 3 个关键词足以锚定一个搜索维度的主题，同时保持搜索引擎的匹配灵活性
- 示例改进：`"{stock_name} 重大事件 并购重组 管理层变动 战略合作 {year}年"` → `"{stock_name} 并购重组 重大公告 {year}"`

**替代方案**：
- 每维度拆为 2 条子查询（每条 2 关键词）→ 搜索 API 调用翻倍（4→8 次），成本和延迟不可接受
- 使用自然语言句子作为查询 → 博查 API 对自然语言句子的搜索效果未经验证，关键词式查询更可控

### Decision 3: 规则式结果过滤器，位于 Infrastructure 层

**选择**：创建 `SearchResultFilter` 类，位于 `src/modules/research/infrastructure/search_utils/result_filter.py`，通过构造器注入到两个 DataAdapter 中。过滤在 Adapter 内、映射为 Domain DTO 之前执行。

**过滤规则**（按序执行）：
1. **去重**：按 URL 去重，保留首次出现的条目
2. **去空**：剔除 title 为空或全空白的条目
3. **去无内容**：剔除 summary 和 snippet 均为空的条目（无信息量）

**理由**：
- 过滤的是来自外部搜索 API 的原始数据（`WebSearchResultItem`），属于 Infrastructure 层数据清洗职责
- 放在 Adapter 中（而非 ContextBuilder）保持职责分离：Adapter 负责数据质量，ContextBuilder 负责格式化
- 规则简洁可测，不引入模糊判断，避免误杀有价值结果

**扩展点**：`SearchResultFilter` 通过构造器注入到 Adapter。未来若需 LLM 打分，可：
1. 提取 `SearchResultFilter` 的接口为 ABC（或 Protocol）
2. 创建 `LLMSearchResultFilter` 实现
3. 在 DI 容器中替换绑定，Adapter 代码不变

**替代方案**：
- Domain Port + Infrastructure 实现 → 过度抽象：过滤对象是 `WebSearchResultItem`（llm_platform 类型），放入 Domain Port 会引入跨模块 Domain 依赖，违反边界约束
- 在 ContextBuilder 中过滤 → 职责混淆：ContextBuilder 应专注格式化，不应承担数据质量判断

### Decision 4: 结果按时效排序

**选择**：在过滤后、映射为 Domain DTO 前，按 `published_date` 降序排序（最近的在前）。无日期的条目排在末尾。

**理由**：
- LLM 对 Prompt 中靠前的信息通常赋予更高权重（primacy bias）
- 时效越近的信息对宏观/催化剂分析越有价值
- 排序逻辑简单，在 Adapter 中执行，不增加额外复杂度

**替代方案**：
- 在 ContextBuilder 中排序 → 可行但职责不如 Adapter 层清晰
- 不排序 → 放弃低成本的质量提升机会

### Decision 5: 维度参数差异化策略

**选择**：根据维度信息特性，为每个维度配置独立的 `count` 和 `freshness`：

**宏观情报员**：
| 维度 | freshness | count | 理由 |
|------|-----------|-------|------|
| 货币与流动性 | oneMonth | 6 | 货币政策变动频率中等，1 月内足够 |
| 产业政策 | oneMonth | 6 | 政策发布周期较长 |
| 宏观经济 | oneMonth | 6 | GDP/CPI/PMI 按月/季发布 |
| 行业景气 | oneMonth | 6 | 行业趋势变化较慢 |

**催化剂侦探**：
| 维度 | freshness | count | 理由 |
|------|-----------|-------|------|
| 公司重大事件 | oneWeek | 8 | 公司事件时效性强，需要更多近期结果 |
| 行业催化 | oneMonth | 6 | 行业事件变化周期中等 |
| 市场情绪 | oneWeek | 8 | 机构评级/资金流向变化快 |
| 财报预期 | oneMonth | 6 | 财报/业绩预告按季度周期 |

**理由**：
- 公司事件和市场情绪时效性强，用 `oneWeek` + 较多条数捕获近期动态
- 宏观/行业/财报类信息变化较慢，`oneMonth` + 适中条数避免过时信息但保持覆盖
- 降低部分维度的 count（8→6）配合过滤，减少噪音总量

## Risks / Trade-offs

- **[聚焦查询可能遗漏信息]** → 缓解：通过测试对比优化前后的搜索结果质量，必要时微调关键词。查询模板已数据化（Decision 1），调优成本极低。
- **[规则过滤可能误杀有价值结果]** → 缓解：过滤规则保守（仅去重、去空标题、去无内容），不做模糊相关性判断。记录过滤统计日志（过滤前/后数量），便于监控。
- **[freshness=oneWeek 可能返回过少结果]** → 缓解：若某维度在 oneWeek 内结果不足，降级策略已由现有的优雅降级机制覆盖（空维度标记为"信息有限"）。后续可考虑 fallback 到 oneMonth。
- **[两个 Adapter 改动并行]** → 缓解：结构对称，改动模式一致，通过共享 `SearchResultFilter` 和 `SearchDimensionConfig` 减少重复。
