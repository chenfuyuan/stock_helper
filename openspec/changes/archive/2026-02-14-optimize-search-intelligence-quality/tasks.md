## 1. 搜索维度配置数据化

- [x] 1.1 创建 `SearchDimensionConfig` 数据类（`src/modules/research/domain/dtos/search_dimension_config.py`），字段：topic、query_template、count、freshness
- [x] 1.2 定义宏观情报员四维度配置列表（`MACRO_SEARCH_DIMENSIONS`），查询模板遵循聚焦查询规范（核心领域关键词 ≤ 3）
- [x] 1.3 定义催化剂侦探四维度配置列表（`CATALYST_SEARCH_DIMENSIONS`），查询模板遵循聚焦查询规范（核心领域关键词 ≤ 3），所有维度查询包含 stock_name

## 2. 搜索结果过滤器

- [x] 2.1 创建 `SearchResultFilter` 类（`src/modules/research/infrastructure/search_utils/result_filter.py`），实现三条过滤规则：URL 去重、去空标题、去无内容（summary + snippet 均空）
- [x] 2.2 在 `SearchResultFilter` 中实现按 `published_date` 降序排序逻辑（无日期排末尾）
- [x] 2.3 编写 `SearchResultFilter` 单元测试：覆盖去重、去空标题、去无内容、有效条目保留、排序（有日期降序 + 无日期末尾）

## 3. 重构 MacroDataAdapter

- [x] 3.1 修改 `MacroDataAdapter.__init__` 构造函数，新增 `SearchResultFilter` 注入参数
- [x] 3.2 重构 `search_macro_context` 方法：用 `MACRO_SEARCH_DIMENSIONS` 配置驱动搜索循环，替换 inline dict
- [x] 3.3 在 `search_macro_context` 中集成过滤器：搜索结果经过 `SearchResultFilter` 过滤和排序后再映射为 `MacroSearchResultItem`
- [x] 3.4 添加过滤统计日志（INFO 级别：维度名称、过滤前条数、过滤后条数）
- [x] 3.5 更新宏观情报员的 DI 装配（routes 或 container），注入 `SearchResultFilter` 实例

## 4. 重构 CatalystDataAdapter

- [x] 4.1 修改 `CatalystDataAdapter.__init__` 构造函数，新增 `SearchResultFilter` 注入参数
- [x] 4.2 重构 `search_catalyst_context` 方法：用 `CATALYST_SEARCH_DIMENSIONS` 配置驱动搜索循环，替换 inline dict
- [x] 4.3 在 `search_catalyst_context` 中集成过滤器：搜索结果经过 `SearchResultFilter` 过滤和排序后再映射为 `CatalystSearchResultItem`
- [x] 4.4 添加过滤统计日志（INFO 级别：维度名称、过滤前条数、过滤后条数）
- [x] 4.5 更新催化剂侦探的 DI 装配（routes 或 container），注入 `SearchResultFilter` 实例

## 5. 集成测试与配置合规验证

- [x] 5.1 编写配置合规测试：断言每个 `SearchDimensionConfig` 的查询模板核心关键词 ≤ 3、count 在 4-10 范围、freshness 为合法值
- [x] 5.2 编写 MacroDataAdapter 单元测试：mock WebSearchService，断言搜索使用配置中的 count/freshness、结果经过过滤后返回
- [x] 5.3 编写 CatalystDataAdapter 单元测试：mock WebSearchService，断言搜索使用配置中的 count/freshness、结果经过过滤后返回
- [x] 5.4 运行现有宏观情报员和催化剂侦探测试套件，确保无回归
