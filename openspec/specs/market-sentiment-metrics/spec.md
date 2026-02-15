# Spec: market-sentiment-metrics

市场情绪量化指标能力，基于涨停池、炸板池、昨日涨停表现等数据计算连板梯队分布、赚钱效应、炸板率等衍生指标，为超短线交易提供市场情绪洞察。

**测试约定**：每个 `#### Scenario:` 在变更**交付时**须对应至少一个自动化测试用例（单元或集成）；实现顺序可先实现再补测，以完整测试通过为需求完成标准。

---

## ADDED Requirements

### Requirement: ISentimentDataPort 接口定义

系统 MUST 在 `market_insight/domain/ports/sentiment_data_port.py` 中定义 `ISentimentDataPort` ABC 接口，用于从 `data_engineering` 消费市场情绪数据。

该接口 MUST 包含以下方法：

- `get_limit_up_pool(trade_date: date) -> list[LimitUpPoolItemDTO]`：获取指定日期的涨停池数据
- `get_broken_board_pool(trade_date: date) -> list[BrokenBoardItemDTO]`：获取指定日期的炸板池数据
- `get_previous_limit_up(trade_date: date) -> list[PreviousLimitUpItemDTO]`：获取昨日涨停今日表现数据

所有方法 MUST 为异步方法（async）。

`LimitUpPoolItemDTO` 字段 MUST 包含：
- `third_code`（str）、`stock_name`（str）、`pct_chg`（float）、`close`（float）
- `amount`（float）、`consecutive_boards`（int）、`industry`（str）

`BrokenBoardItemDTO` 字段 MUST 包含：
- `third_code`（str）、`stock_name`（str）、`pct_chg`（float）、`close`（float）
- `amount`（float）、`open_count`（int）、`industry`（str）

`PreviousLimitUpItemDTO` 字段 MUST 包含：
- `third_code`（str）、`stock_name`（str）、`pct_chg`（float）、`close`（float）
- `amount`（float）、`yesterday_consecutive_boards`（int）、`industry`（str）

DTO MUST 定义在 `market_insight/domain/dtos/sentiment_dtos.py` 中，不直接引用 `data_engineering` 的类型。

#### Scenario: Port 在 Market Insight Domain 层定义

- **WHEN** 检查 `ISentimentDataPort` 的定义位置
- **THEN** MUST 位于 `market_insight/domain/ports/sentiment_data_port.py`
- **THEN** 返回类型 MUST 使用 `market_insight` 领域层 DTO

---

### Requirement: DeSentimentDataAdapter 适配器实现

系统 MUST 在 `market_insight/infrastructure/adapters/de_sentiment_data_adapter.py` 中实现 `DeSentimentDataAdapter`，实现 `ISentimentDataPort` 接口。

该适配器 MUST 通过 `DataEngineeringContainer` 获取以下查询用例并调用：
- `GetLimitUpPoolByDateUseCase` → 转换为 `LimitUpPoolItemDTO`
- `GetBrokenBoardByDateUseCase` → 转换为 `BrokenBoardItemDTO`
- `GetPreviousLimitUpByDateUseCase` → 转换为 `PreviousLimitUpItemDTO`

MUST 将 `data_engineering` 的领域实体转换为 `market_insight` 的领域层 DTO。

#### Scenario: 正常获取涨停池数据

- **WHEN** 调用 `get_limit_up_pool(date(2024, 2, 15))`
- **THEN** 系统 MUST 通过 DE 查询用例获取数据并转换为 `list[LimitUpPoolItemDTO]`

#### Scenario: DE 查询无数据

- **WHEN** 调用 `get_limit_up_pool` 但 DE 中无对应日期数据
- **THEN** 系统 MUST 返回空列表

---

### Requirement: SentimentAnalyzer 领域服务

系统 MUST 在 `market_insight/domain/services/sentiment_analyzer.py` 中实现 `SentimentAnalyzer` 领域服务。

该服务 MUST 提供以下方法：

1. `analyze_consecutive_board_ladder(limit_up_pool: list[LimitUpPoolItemDTO]) -> ConsecutiveBoardLadder`

   计算连板梯队分布。`ConsecutiveBoardLadder` 字段 MUST 包含：
   - `max_height`（int）：当日最高连板高度
   - `tiers`（list[BoardTier]）：各梯队统计，每项含 `board_count`（int，连板天数）和 `stocks`（list[str]，股票名称列表）
   - `total_limit_up_count`（int）：涨停总家数

   `tiers` MUST 按 `board_count` 降序排列。

2. `analyze_previous_limit_up_performance(previous_limit_up: list[PreviousLimitUpItemDTO]) -> PreviousLimitUpPerformance`

   计算昨日涨停今日表现。`PreviousLimitUpPerformance` 字段 MUST 包含：
   - `total_count`（int）：昨日涨停总数
   - `up_count`（int）：今日上涨家数（pct_chg > 0）
   - `down_count`（int）：今日下跌家数（pct_chg < 0）
   - `avg_pct_chg`（float）：平均涨跌幅
   - `profit_rate`（float）：赚钱效应（上涨家数 / 总数 × 100）
   - `strongest`（list[PreviousLimitUpItemDTO]）：今日涨幅最大的前 5 只
   - `weakest`（list[PreviousLimitUpItemDTO]）：今日跌幅最大的前 5 只

3. `analyze_broken_board(limit_up_pool: list[LimitUpPoolItemDTO], broken_board_pool: list[BrokenBoardItemDTO]) -> BrokenBoardAnalysis`

   计算炸板分析。`BrokenBoardAnalysis` 字段 MUST 包含：
   - `broken_count`（int）：炸板家数
   - `total_attempted`（int）：曾触板总家数（涨停家数 + 炸板家数）
   - `broken_rate`（float）：炸板率（炸板家数 / 曾触板总家数 × 100）
   - `broken_stocks`（list[BrokenBoardItemDTO]）：炸板股列表

所有分析方法 MUST 为纯函数式计算，不依赖外部 I/O。

上述结果 DTO MUST 定义在 `market_insight/domain/dtos/sentiment_dtos.py` 中。

#### Scenario: 连板梯队分布计算

- **WHEN** 涨停池中有 3 只 1 板股、2 只 2 连板股、1 只 5 连板股
- **THEN** `max_height` MUST 为 5，`tiers` MUST 包含 3 个梯队（5连板→2连板→1板），`total_limit_up_count` 为 6

#### Scenario: 涨停池为空

- **WHEN** 涨停池数据为空列表
- **THEN** `max_height` MUST 为 0，`tiers` 为空列表，`total_limit_up_count` 为 0

#### Scenario: 昨日涨停表现计算

- **WHEN** 昨日 10 只涨停股今日 7 只上涨、3 只下跌
- **THEN** `profit_rate` MUST 为 70.0，`up_count` 为 7，`down_count` 为 3

#### Scenario: 昨日涨停为空

- **WHEN** 昨日涨停表现数据为空列表
- **THEN** `total_count` 为 0，`profit_rate` 为 0.0

#### Scenario: 炸板率计算

- **WHEN** 涨停池有 20 只，炸板池有 5 只
- **THEN** `total_attempted` MUST 为 25，`broken_rate` MUST 为 20.0

#### Scenario: 无炸板

- **WHEN** 炸板池为空，涨停池有 15 只
- **THEN** `broken_rate` MUST 为 0.0

#### Scenario: 单只股票的连板梯队

- **WHEN** 涨停池中仅有 1 只 3 连板股
- **THEN** `max_height` MUST 为 3，`tiers` 包含 1 个梯队，`total_limit_up_count` 为 1

#### Scenario: 昨日涨停表现含平盘股

- **WHEN** 昨日 5 只涨停股今日 2 只上涨、2 只下跌、1 只平盘（pct_chg = 0）
- **THEN** `up_count` 为 2，`down_count` 为 2，`total_count` 为 5，`profit_rate` MUST 为 40.0

#### Scenario: 昨日涨停 strongest/weakest 不足 5 只

- **WHEN** 昨日仅 3 只涨停股
- **THEN** `strongest` 和 `weakest` 列表长度 MUST 均为 3（返回所有可用数据，不补齐）

#### Scenario: 涨停池和炸板池均为空

- **WHEN** 涨停池和炸板池数据均为空列表
- **THEN** `total_attempted` 为 0，`broken_rate` MUST 为 0.0（除零安全）

---

### Requirement: GetSentimentMetricsQuery 查询用例

系统 MUST 在 `market_insight/application/queries/get_sentiment_metrics_query.py` 中实现 `GetSentimentMetricsQuery`。

接口签名：
```
execute(trade_date: date) -> SentimentMetricsDTO
```

该用例 MUST：
1. 通过 `ISentimentDataPort` 获取涨停池、炸板池、昨日涨停表现数据
2. 调用 `SentimentAnalyzer` 计算各项衍生指标
3. 组装并返回 `SentimentMetricsDTO`

`SentimentMetricsDTO` 为 Application 层 DTO，字段 MUST 包含：
- `trade_date`（date）
- `consecutive_board_ladder`（ConsecutiveBoardLadderDTO）：连板梯队
- `previous_limit_up_performance`（PreviousLimitUpPerformanceDTO）：昨日涨停表现
- `broken_board_analysis`（BrokenBoardAnalysisDTO）：炸板分析

Application 层 DTO MUST 定义在 `market_insight/application/dtos/sentiment_metrics_dtos.py` 中。

#### Scenario: 正常查询情绪指标

- **WHEN** 调用 `execute(date(2024, 2, 15))`，DE 中存在对应数据
- **THEN** 系统 MUST 返回包含三项分析结果的 `SentimentMetricsDTO`

#### Scenario: 部分数据缺失

- **WHEN** 调用 `execute`，涨停池有数据但炸板池无数据
- **THEN** 系统 MUST 正常返回结果，炸板分析中 `broken_count` 为 0，`broken_rate` 为 0.0
