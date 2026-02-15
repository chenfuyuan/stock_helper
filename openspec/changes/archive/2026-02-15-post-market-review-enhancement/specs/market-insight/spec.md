## MODIFIED Requirements

### Requirement: GenerateDailyReportCmd 应用命令

系统 MUST 在 `market_insight/application/commands/generate_daily_report_cmd.py` 中实现 `GenerateDailyReportCmd`。

该命令 MUST 编排以下完整流程：

1. 通过 `IMarketDataPort` 获取指定日期的全市场日线数据
2. 通过 `IConceptDataPort` 获取所有概念及其成分股映射
3. 构建 `concept_stock_map`（以 third_code 为 key 的反向索引）
4. 调用 `ConceptHeatCalculator.calculate()` 计算板块热度
5. 调用 `LimitUpScanner.scan()` 扫描涨停股
6. 通过 `IConceptHeatRepository.save_all()` 持久化热度数据
7. 通过 `ILimitUpRepository.save_all()` 持久化涨停数据
8. **通过 `ISentimentDataPort` 获取涨停池、炸板池、昨日涨停表现数据**
9. **调用 `SentimentAnalyzer` 计算情绪衍生指标（连板梯队、赚钱效应、炸板率）**
10. **通过 `ICapitalFlowDataPort` 获取龙虎榜和板块资金流向数据**
11. **调用 `CapitalFlowAnalyzer` 计算资金行为分析结果**
12. 调用报告生成器输出 Markdown 日报（传入所有分析结果）
13. 返回执行结果摘要

步骤 8-11 的数据获取 MUST 做异常隔离：单项数据获取或分析失败 MUST NOT 中断整个流程，失败项记录 WARNING 日志，对应报告章节标注"数据暂不可用"。

接口签名：

```
execute(trade_date: date) -> DailyReportResult
```

`DailyReportResult` 为 Application 层 DTO，字段 MUST 包含：

- `trade_date`（date）：交易日期
- `concept_count`（int）：参与计算的概念数量
- `limit_up_count`（int）：涨停股数量
- `report_path`（str）：生成的 Markdown 文件路径
- `elapsed_seconds`（float）：总执行耗时（秒）
- **`sentiment_available`（bool）：情绪数据是否可用**
- **`capital_flow_available`（bool）：资金数据是否可用**

#### Scenario: 完整流程包含情绪与资金数据

- **WHEN** 调用 `execute(date(2024, 2, 15))`，所有数据源正常
- **THEN** 系统 MUST 执行全部 13 个步骤，生成包含情绪和资金章节的完整报告，`sentiment_available` 和 `capital_flow_available` 均为 True

#### Scenario: 情绪数据获取失败但不中断流程

- **WHEN** 调用 `execute`，步骤 8 的 `ISentimentDataPort` 抛出异常
- **THEN** 系统 MUST 跳过步骤 8-9，继续执行步骤 10-13，`sentiment_available` 为 False，报告中情绪章节标注"数据暂不可用"

#### Scenario: 资金数据获取失败但不中断流程

- **WHEN** 调用 `execute`，步骤 10 的 `ICapitalFlowDataPort` 抛出异常
- **THEN** 系统 MUST 跳过步骤 10-11，继续执行步骤 12-13，`capital_flow_available` 为 False，报告中资金章节标注"数据暂不可用"

---

### Requirement: MarkdownReportGenerator 报告生成器

系统 MUST 在 `market_insight/infrastructure/report/markdown_report_generator.py` 中实现 `MarkdownReportGenerator`。

该生成器 MUST 根据板块热度、涨停数据、**市场情绪分析**和**资金行为分析**生成结构化 Markdown 文件。

输出文件路径格式：`{output_dir}/YYYY-MM-DD-market-insight.md`

报告 MUST 包含以下章节：

1. **标题**：`# 每日市场洞察 - YYYY-MM-DD`
2. **Top N 强势概念**：按 `avg_pct_chg` 降序，以表格形式展示排名、概念名称、涨跌幅、涨停家数、成交额。默认 Top 10。
3. **今日涨停天梯**：按概念分组展示涨停股。每个概念下列出涨停股名称、代码、涨跌幅。
4. **市场情绪**（新增）：
   - **连板梯队**：展示最高连板高度，按梯队（从高到低）列出各高度的股票名称
   - **昨日涨停表现**：展示赚钱效应（上涨/下跌/平均涨跌幅），最强与最弱股票
   - **炸板分析**：展示炸板率、炸板家数、炸板股列表
5. **资金动向**（新增）：
   - **龙虎榜**：展示净买入/净卖出前 N 个股，机构参与个股
   - **板块资金流向**：展示净流入/净流出前 N 板块
6. **市场概览**：涨停总数、概念板块总数等统计信息。
7. **数据更新时间**：报告生成时间戳。

当情绪或资金数据不可用时，对应章节 MUST 显示"⚠️ 数据暂不可用"提示文本，而非省略整个章节。

#### Scenario: 完整报告生成

- **WHEN** 传入完整的热度、涨停、情绪、资金分析数据
- **THEN** 生成的 Markdown MUST 包含上述全部 7 个章节

#### Scenario: 情绪数据不可用

- **WHEN** 情绪分析结果为 None
- **THEN** "市场情绪"章节 MUST 显示"⚠️ 数据暂不可用"

#### Scenario: 资金数据不可用

- **WHEN** 资金分析结果为 None
- **THEN** "资金动向"章节 MUST 显示"⚠️ 数据暂不可用"

---

### Requirement: MarketInsightContainer DI 容器

系统 MUST 在 `market_insight/container.py` 中实现 `MarketInsightContainer`。

该容器 MUST 注册以下依赖：

- `DeConceptDataAdapter` 作为 `IConceptDataPort` 的实现
- `DeMarketDataAdapter` 作为 `IMarketDataPort` 的实现
- **`DeSentimentDataAdapter` 作为 `ISentimentDataPort` 的实现**
- **`DeCapitalFlowDataAdapter` 作为 `ICapitalFlowDataPort` 的实现**
- `PgConceptHeatRepository` 作为 `IConceptHeatRepository` 的实现
- `PgLimitUpRepository` 作为 `ILimitUpRepository` 的实现
- `ConceptHeatCalculator` 领域服务
- `LimitUpScanner` 领域服务
- **`SentimentAnalyzer` 领域服务**
- **`CapitalFlowAnalyzer` 领域服务**
- `MarkdownReportGenerator` 报告生成器
- `GenerateDailyReportCmd` 应用命令
- `GetConceptHeatQuery` 查询用例
- `GetLimitUpQuery` 查询用例
- **`GetSentimentMetricsQuery` 查询用例**
- **`GetCapitalFlowAnalysisQuery` 查询用例**

容器 MUST 接受 `AsyncSession` 和 `DataEngineeringContainer` 作为构造参数。

#### Scenario: 容器注册完整性

- **WHEN** 通过 `MarketInsightContainer` 获取 `GenerateDailyReportCmd`
- **THEN** 系统 MUST 返回正确装配的实例，内部注入了所有新增的 Port 实现和领域服务

---

### Requirement: REST API 端点

系统 MUST 在 `market_insight/presentation/rest/market_insight_router.py` 中实现 FastAPI Router。

Router 前缀 MUST 为 `/api/market-insight`。

MUST 提供以下端点：

| 端点 | 方法 | 参数 | 返回 |
|------|------|------|------|
| `/concept-heat` | GET | `trade_date: date`（必填）、`top_n: int`（可选，默认 10） | `list[ConceptHeatDTO]` |
| `/limit-up` | GET | `trade_date: date`（必填）、`concept_code: str`（可选） | `list[LimitUpStockDTO]` |
| `/daily-report` | POST | `trade_date: date`（必填） | `DailyReportResult` |
| **`/sentiment-metrics`** | **GET** | **`trade_date: date`（必填）** | **`SentimentMetricsDTO`** |
| **`/capital-flow`** | **GET** | **`trade_date: date`（必填）** | **`CapitalFlowAnalysisDTO`** |

所有端点 MUST 使用 Pydantic 响应模型。

#### Scenario: 查询情绪指标

- **WHEN** GET `/api/market-insight/sentiment-metrics?trade_date=2024-02-15`
- **THEN** 系统 MUST 返回 200 和 `SentimentMetricsDTO` JSON 响应

#### Scenario: 查询资金分析

- **WHEN** GET `/api/market-insight/capital-flow?trade_date=2024-02-15`
- **THEN** 系统 MUST 返回 200 和 `CapitalFlowAnalysisDTO` JSON 响应
