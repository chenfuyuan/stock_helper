# Spec: research-search-quality

Research 模块搜索质量基线：定义宏观情报员和催化剂侦探在执行 Web 搜索时的查询构造规范、搜索参数配置标准、搜索结果过滤规则和结果排序策略。本 spec 为两个软情报专家的搜索策略提供统一的质量约束，不改变搜索 API 契约（`WebSearchRequest` / `WebSearchResponse`），仅优化搜索输入（查询词）和搜索输出（结果过滤与排序）。

**归属模块**：Research（`src/modules/research/`）。过滤器实现位于 Infrastructure 层，配置数据类位于 Domain DTO 层。

**测试约定**：每个 `#### Scenario:` 在变更**交付时**须对应至少一个自动化测试用例（单元或集成）；实现顺序可先实现再补测，以完整测试通过为需求完成标准。

---

## ADDED Requirements

### Requirement: 搜索维度配置数据化

每个搜索维度的配置（维度主题 topic、查询模板 query_template、返回条数 count、时效过滤 freshness）SHALL 定义为结构化的数据类（如 `SearchDimensionConfig`），位于 Research 的 `domain/dtos/` 中。DataAdapter SHALL 基于该配置列表驱动搜索循环，SHALL NOT 将查询模板和参数以 inline dict 或硬编码字符串的方式散布在方法体中。

#### Scenario: 配置驱动搜索循环

- **WHEN** DataAdapter 执行多维度搜索
- **THEN** 每个维度的搜索查询词、count、freshness SHALL 来自对应的 `SearchDimensionConfig` 实例，而非方法内的字面量

#### Scenario: 配置可独立测试

- **WHEN** 运行搜索质量相关测试套件
- **THEN** 存在测试用例：直接断言每个维度的 `SearchDimensionConfig` 配置合理性（如查询模板关键词数量、count 范围、freshness 合法值）

---

### Requirement: 聚焦查询构造规范

每个搜索维度的查询模板 SHALL 遵循以下规范：
1. **核心领域关键词不超过 3 个**：查询模板中的核心领域关键词（不计 stock_name、industry、year 等上下文填充词）SHALL 不超过 3 个。
2. **禁止关键词堆砌**：SHALL NOT 在同一查询中塞入 4 个或以上描述不同子主题的领域关键词（如同时包含"并购重组"、"管理层变动"、"战略合作"、"公司治理"）。
3. **上下文词保留**：stock_name、industry、year 作为搜索上下文锚点，不计入核心关键词限制。

#### Scenario: 查询模板关键词数量合规

- **WHEN** 检查任一维度的查询模板
- **THEN** 模板中的核心领域关键词 SHALL 不超过 3 个（不计 stock_name、industry、year 占位符）

#### Scenario: 不同维度的查询聚焦于各自主题

- **WHEN** 比较同一专家的四个维度查询模板
- **THEN** 每个维度的查询 SHALL 聚焦于该维度主题（如货币政策维度不包含行业景气关键词），维度间关键词 SHALL NOT 大量重叠

---

### Requirement: 维度级搜索参数差异化

每个搜索维度 SHALL 定义独立的 `count`（返回条数）和 `freshness`（时效过滤）参数，根据该维度信息的时效特性进行差异化配置。SHALL NOT 对所有维度使用统一的 count 和 freshness。

参数配置 SHALL 遵循以下原则：
- 时效性强的维度（如公司重大事件、市场情绪）SHALL 使用更短的 freshness（如 `oneWeek`）和较高的 count
- 变化周期较长的维度（如宏观经济、行业景气）SHALL 使用较长的 freshness（如 `oneMonth`）和适中的 count

#### Scenario: 不同维度使用不同参数

- **WHEN** 催化剂侦探执行四个维度的搜索
- **THEN** 公司重大事件维度和市场情绪维度的 freshness SHALL 短于行业催化维度和财报预期维度的 freshness

#### Scenario: count 值在合理范围内

- **WHEN** 检查任一维度的 count 配置
- **THEN** count SHALL 在 4 到 10 之间（过少信息不足，过多噪音增加）

---

### Requirement: 搜索结果规则式过滤

DataAdapter 在将搜索结果映射为 Domain DTO 之前，SHALL 对原始搜索结果执行过滤。过滤 SHALL 按以下规则顺序执行：

1. **URL 去重**：同一 URL 的搜索结果仅保留首次出现的条目。
2. **去空标题**：title 为空或全空白的条目 SHALL 被剔除。
3. **去无内容**：summary 和 snippet 均为空或全空白的条目 SHALL 被剔除（无信息量，无法贡献上下文）。

过滤 SHALL NOT 执行模糊相关性判断（如关键词匹配评分），仅做确定性规则过滤。

#### Scenario: URL 去重

- **WHEN** 搜索结果中存在多条 URL 相同的条目
- **THEN** 过滤后仅保留首次出现的条目，后续重复条目 SHALL 被剔除

#### Scenario: 空标题条目被剔除

- **WHEN** 搜索结果中存在 title 为空字符串或全空白的条目
- **THEN** 该条目 SHALL 被过滤器剔除

#### Scenario: 无内容条目被剔除

- **WHEN** 搜索结果中存在 summary 和 snippet 均为空或全空白的条目
- **THEN** 该条目 SHALL 被过滤器剔除

#### Scenario: 有效条目不被误杀

- **WHEN** 搜索结果中存在 title 非空且 summary 或 snippet 至少有一个非空的条目
- **THEN** 该条目 SHALL 通过过滤，不被剔除

---

### Requirement: 过滤器通过构造器注入到 DataAdapter

搜索结果过滤器 SHALL 通过构造器注入到 `MacroDataAdapter` 和 `CatalystDataAdapter`，SHALL NOT 在 Adapter 内部直接实例化。过滤器实现位于 Research 的 Infrastructure 层（如 `infrastructure/search_utils/result_filter.py`）。

这一注入设计为未来替换实现（如 LLM 打分过滤器）保留扩展点：替换时仅需在 DI 容器中更改绑定，Adapter 代码无需修改。

#### Scenario: 过滤器通过构造器注入

- **WHEN** 查看 `MacroDataAdapter` 和 `CatalystDataAdapter` 的构造函数
- **THEN** 两者 SHALL 接受过滤器实例作为构造参数，SHALL NOT 在方法体内直接实例化过滤器

#### Scenario: 过滤器可被替换

- **WHEN** 需要将规则式过滤器替换为其他实现（如 LLM 打分过滤器）
- **THEN** 仅需在 DI 容器 / 装配层更改注入的过滤器实例，DataAdapter 的代码 SHALL NOT 需要修改

---

### Requirement: 过滤后结果按时效排序

DataAdapter 在过滤完成后、映射为 Domain DTO 前，SHALL 对结果按 `published_date` 降序排列（最近发布的在前）。无 `published_date` 的条目 SHALL 排在有日期条目之后。

#### Scenario: 有日期的结果按时间降序排列

- **WHEN** 过滤后的搜索结果中包含多条有 `published_date` 的条目
- **THEN** 映射为 Domain DTO 后的列表中，发布日期较近的条目 SHALL 排在较早的条目之前

#### Scenario: 无日期的结果排在末尾

- **WHEN** 过滤后的搜索结果中既有有日期的条目也有无日期的条目
- **THEN** 无日期的条目 SHALL 排在所有有日期条目之后

---

### Requirement: 过滤统计日志

DataAdapter 在执行过滤后 SHALL 记录过滤统计日志（INFO 级别），包含：维度名称、过滤前条数、过滤后条数。便于监控过滤效果和排查过滤误杀。

#### Scenario: 过滤统计被记录

- **WHEN** 某维度的搜索结果经过过滤
- **THEN** 系统 SHALL 记录 INFO 日志，包含该维度名称、过滤前条目数和过滤后条目数

---

### Requirement: 可测性 — Scenario 与测试一一对应

每个上述 Scenario 在变更交付时 SHALL 对应至少一个自动化测试（单元或集成）；需求完成的验收条件包含「该需求下所有 Scenario 的测试通过」。实现时可采用先实现再补测，不强制测试先行。

#### Scenario: 测试覆盖过滤规则

- **WHEN** 运行搜索质量相关测试套件
- **THEN** 存在测试用例：构造含重复 URL、空标题、无内容的搜索结果列表，断言过滤器正确剔除不合格条目且保留有效条目

#### Scenario: 测试覆盖排序逻辑

- **WHEN** 运行搜索质量相关测试套件
- **THEN** 存在测试用例：构造含不同 published_date 和无日期的搜索结果列表，断言排序后有日期的按降序排列、无日期的在末尾

#### Scenario: 测试覆盖配置合规性

- **WHEN** 运行搜索质量相关测试套件
- **THEN** 存在测试用例：断言每个维度的 SearchDimensionConfig 的查询模板核心关键词不超过 3 个、count 在合理范围、freshness 为合法值
