# Delta Spec: research-macro-intelligence

本变更优化宏观情报员的搜索策略，使其查询构造、搜索参数和结果处理符合 `research-search-quality` 定义的质量基线。

---

## MODIFIED Requirements

### Requirement: 多维度宏观搜索策略

宏观情报员 SHALL 基于标的行业上下文，按**四个宏观维度**分别构建搜索查询并执行 Web 搜索：
1. **货币与流动性环境**：央行货币政策、利率、流动性相关
2. **产业政策与监管动态**：该行业的产业政策、监管政策相关
3. **宏观经济周期定位**：GDP、CPI、PMI 等宏观经济指标相关
4. **行业景气与资金流向**：该行业的景气度、发展趋势、市场前景相关

搜索查询 SHALL 由代码根据标的行业（industry）和当前年份动态生成。每个维度的查询模板 SHALL 遵循 `research-search-quality` 定义的聚焦查询构造规范（核心领域关键词不超过 3 个，禁止关键词堆砌）。每个维度 SHALL 使用独立的 `count` 和 `freshness` 参数（由 `SearchDimensionConfig` 定义），并启用 AI 摘要。

搜索结果 SHALL 在映射为 Domain DTO 之前，经过 `research-search-quality` 定义的规则式过滤（URL 去重、去空标题、去无内容）和按时效排序处理。

#### Scenario: 按四个维度分别搜索

- **WHEN** 宏观情报员执行分析流程并需要获取宏观情报
- **THEN** 系统 SHALL 针对四个维度分别执行 Web 搜索（共 4 次搜索调用），每次搜索的查询词包含标的行业上下文

#### Scenario: 搜索查询包含行业上下文

- **WHEN** 标的属于"银行"行业
- **THEN** 产业政策维度的搜索查询 SHALL 包含"银行"关键词；行业景气维度的搜索查询 SHALL 包含"银行"关键词

#### Scenario: 搜索使用时效过滤

- **WHEN** 系统执行宏观搜索
- **THEN** 搜索请求 SHALL 设置 freshness 参数，以获取近期宏观信息而非过时数据

#### Scenario: 查询模板符合聚焦查询规范

- **WHEN** 检查宏观情报员四个维度的查询模板
- **THEN** 每个维度的查询模板核心领域关键词 SHALL 不超过 3 个（不计 industry、year 等上下文占位符）

#### Scenario: 搜索参数按维度差异化配置

- **WHEN** 宏观情报员执行四个维度的搜索
- **THEN** 每个维度 SHALL 使用各自 `SearchDimensionConfig` 中定义的 count 和 freshness，SHALL NOT 所有维度使用相同参数

#### Scenario: 搜索结果经过过滤后送入上下文构建

- **WHEN** 某维度搜索返回原始结果
- **THEN** 系统 SHALL 对结果执行过滤（URL 去重、去空标题、去无内容）后，再映射为 `MacroSearchResultItem` 并送入上下文构建器
