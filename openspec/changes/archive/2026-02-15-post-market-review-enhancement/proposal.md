## Why

当前 `market_insight` 模块仅覆盖**概念热度**和**涨停扫描**两个基础维度，属于"现象描述"层面。对于超短线交易的盘后复盘而言，缺少**市场情绪量化**（连板梯队、昨日涨停表现、炸板率）和**主力资金行为**（龙虎榜、资金流向）两大关键数据维度，无法提供深度市场洞察和次日交易决策支持。

通过引入 AkShare 作为增强数据源，可在极低成本下（免费 API）补齐这些维度，将复盘系统从"数据罗列"升级为"深度洞察"。

## What Changes

- **`data_engineering` 新增 AkShare 数据采集与落库**：在 `data_engineering/infrastructure/` 下新增 AkShare 客户端与适配器，负责从东方财富等数据源采集连板池、炸板池、昨日涨停表现、龙虎榜、资金流向等原始数据，并持久化至 PostgreSQL。遵循现有 Tushare 数据源的架构模式（Port → Adapter → Repository → ORM Model）
- **`data_engineering` 新增数据查询用例**：为上述新数据提供 Application 层查询用例，供 `market_insight` 通过 Ports 消费
- **`market_insight` 新增市场情绪量化能力**：连板梯队统计（最高连板高度、各梯队分布）、昨日涨停次日表现（涨停溢价率、赚钱效应）、炸板率及炸板股分析（基于 `data_engineering` 提供的数据）
- **`market_insight` 新增主力资金行为分析能力**：龙虎榜数据解析（机构/游资席位净买卖）、板块/个股维度的资金净流入估算
- **扩展每日复盘报告**：将情绪与资金数据维度整合到现有 `GenerateDailyReportCmd` 流程和 Markdown 报告中
- **新增 `akshare` 依赖**：在项目依赖中加入 `akshare` 库
- **不含新闻快讯**：事件新闻关联将由后续独立模块承担，本次变更不涉及

## Capabilities

### New Capabilities

- `akshare-data-sync`：AkShare 数据采集与落库——在 `data_engineering` 模块中实现 AkShare 数据源的接入，包括连板池、炸板池、昨日涨停表现、龙虎榜、资金流向等数据的采集、持久化和查询
- `market-sentiment-metrics`：市场情绪量化指标——基于 `data_engineering` 提供的连板池/炸板池/昨日涨停数据，在 `market_insight` 中计算连板梯队分布、赚钱/亏钱效应、炸板率等衍生指标
- `capital-flow-analysis`：主力资金行为分析——基于 `data_engineering` 提供的龙虎榜与资金流向数据，在 `market_insight` 中进行机构/游资席位解析、板块资金净流入估算

### Modified Capabilities

- `market-insight`：扩展 `GenerateDailyReportCmd` 编排流程以整合新数据维度；扩展 `MarkdownReportGenerator` 输出新增的情绪/资金章节；新增对应的查询用例与 REST API 端点
- `de-data-sync`：扩展 `data_engineering` 的数据同步能力，新增 AkShare 数据源的同步调度入口

## Impact

- **代码变更范围**：涉及 `data_engineering` 和 `market_insight` 两个模块
  - `data_engineering`：新增 AkShare 客户端、数据采集适配器、ORM 模型、Repository 实现、查询用例、DI 容器扩展
  - `market_insight`：新增 Domain Ports（消费 DE 新数据）、领域服务（情绪/资金分析）、适配器；修改 `GenerateDailyReportCmd`、`MarkdownReportGenerator`、`MarketInsightContainer`、REST Router
- **新增外部依赖**：`akshare` Python 库（通过 pip 安装，归属 `data_engineering` 模块）
- **数据库变更**：
  - `data_engineering` 侧：新增 `de_limit_up_pool`（涨停池/连板池）、`de_broken_board_pool`（炸板池）、`de_previous_limit_up`（昨日涨停表现）、`de_dragon_tiger`（龙虎榜）、`de_capital_flow`（资金流向）等表
  - `market_insight` 侧：可能新增衍生指标的汇总表
- **API 变更**：新增 `market_insight` 查询端点（情绪指标、龙虎榜、资金流向）；`/daily-report` 响应 DTO 可能扩展字段
- **外部 API 依赖**：运行时需要网络访问 AkShare 抓取的数据源（东方财富等），需考虑限流与异常处理
- **不影响**：现有 Tushare 数据流不受影响；`data_engineering` 现有功能不变；其他模块无需改动
