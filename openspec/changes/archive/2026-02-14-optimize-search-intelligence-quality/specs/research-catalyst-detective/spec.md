# Delta Spec: research-catalyst-detective

本变更优化催化剂侦探的搜索策略，使其查询构造、搜索参数和结果处理符合 `research-search-quality` 定义的质量基线。

---

## MODIFIED Requirements

### Requirement: 多维度催化剂搜索策略

催化剂侦探 SHALL 基于标的**公司名称**与行业上下文，按**四个催化维度**分别构建搜索查询并执行 Web 搜索：
1. **公司重大事件与动态**：并购重组、管理层变动、战略转型、公司治理等
2. **行业催化与竞争格局**：行业政策催化、技术突破、竞争对手动态、供应链变化等
3. **市场情绪与机构动向**：分析师评级、机构调研、市场热点联动、大宗交易异动等
4. **财报预期与业绩催化**：业绩预告/快报、盈利趋势、关键财务事件、订单/合同催化等

搜索查询 SHALL 由代码根据标的**公司名称**（stock_name）、行业（industry）和当前年份动态生成。**所有维度的搜索查询 SHALL 包含公司名称**，以聚焦个股级催化事件（区别于宏观情报员仅以行业关键词搜索）。每个维度的查询模板 SHALL 遵循 `research-search-quality` 定义的聚焦查询构造规范（核心领域关键词不超过 3 个，禁止关键词堆砌）。每个维度 SHALL 使用独立的 `count` 和 `freshness` 参数（由 `SearchDimensionConfig` 定义），并启用 AI 摘要。

搜索结果 SHALL 在映射为 Domain DTO 之前，经过 `research-search-quality` 定义的规则式过滤（URL 去重、去空标题、去无内容）和按时效排序处理。

#### Scenario: 按四个维度分别搜索

- **WHEN** 催化剂侦探执行分析流程并需要获取催化事件情报
- **THEN** 系统 SHALL 针对四个维度分别执行 Web 搜索（共 4 次搜索调用），每次搜索的查询词包含标的公司名称

#### Scenario: 搜索查询包含公司名称

- **WHEN** 标的为"平安银行"（行业：银行）
- **THEN** 所有四个维度的搜索查询 SHALL 包含"平安银行"关键词；行业催化维度的搜索查询 SHALL 同时包含"银行"行业关键词

#### Scenario: 搜索使用时效过滤

- **WHEN** 系统执行催化剂搜索
- **THEN** 搜索请求 SHALL 设置 freshness 参数，以获取近期催化事件信息而非过时数据

#### Scenario: 查询模板符合聚焦查询规范

- **WHEN** 检查催化剂侦探四个维度的查询模板
- **THEN** 每个维度的查询模板核心领域关键词 SHALL 不超过 3 个（不计 stock_name、industry、year 等上下文占位符）

#### Scenario: 搜索参数按维度差异化配置

- **WHEN** 催化剂侦探执行四个维度的搜索
- **THEN** 公司重大事件维度和市场情绪维度的 freshness SHALL 短于行业催化维度和财报预期维度的 freshness；每个维度 SHALL 使用各自 `SearchDimensionConfig` 中定义的 count 和 freshness

#### Scenario: 搜索结果经过过滤后送入上下文构建

- **WHEN** 某维度搜索返回原始结果
- **THEN** 系统 SHALL 对结果执行过滤（URL 去重、去空标题、去无内容）后，再映射为 `CatalystSearchResultItem` 并送入上下文构建器
