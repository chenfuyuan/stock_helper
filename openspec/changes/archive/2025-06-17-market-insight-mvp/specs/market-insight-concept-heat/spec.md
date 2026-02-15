# Purpose

`market_insight` 模块的概念板块热度计算能力。从 `data_engineering` 获取概念成分股映射与日线行情数据，通过等权平均法聚合板块涨跌幅，输出板块热度排名并持久化至 PostgreSQL。

## ADDED Requirements

### Requirement: IConceptDataPort 接口定义

系统 MUST 在 `market_insight/domain/ports/concept_data_port.py` 中定义 `IConceptDataPort` ABC 接口，用于获取概念板块及其成分股映射。

该接口 MUST 包含以下方法：

- `get_all_concepts_with_stocks() -> list[ConceptWithStocksDTO]`：获取所有概念板块及其成分股列表。

`ConceptWithStocksDTO` 为 `market_insight` 领域层 DTO，字段 MUST 包含：

- `code`（str）：概念板块代码
- `name`（str）：概念板块名称
- `stocks`（list[ConceptStockDTO]）：成分股列表，每项含 `third_code`（str）和 `stock_name`（str）

方法 MUST 为异步方法（async）。

#### Scenario: Port 在 Market Insight Domain 层定义

- **WHEN** 检查 `IConceptDataPort` 的定义位置
- **THEN** MUST 位于 `src/modules/market_insight/domain/ports/concept_data_port.py`
- **THEN** 接口返回类型 MUST 使用 `market_insight` 领域层定义的 DTO，不直接引用 `data_engineering` 的类型

### Requirement: IMarketDataPort 接口定义

系统 MUST 在 `market_insight/domain/ports/market_data_port.py` 中定义 `IMarketDataPort` ABC 接口，用于获取指定日期的全市场日线行情。

该接口 MUST 包含以下方法：

- `get_daily_bars_by_date(trade_date: date) -> list[StockDailyDTO]`：获取指定交易日全市场日线数据。

`StockDailyDTO` 为 `market_insight` 领域层 DTO，字段 MUST 包含：

- `third_code`（str）：股票代码（系统标准格式）
- `stock_name`（str）：股票名称
- `trade_date`（date）：交易日期
- `close`（float）：收盘价
- `pct_chg`（float）：涨跌幅（百分比）
- `amount`（float）：成交额

方法 MUST 为异步方法（async）。

#### Scenario: Port 在 Market Insight Domain 层定义

- **WHEN** 检查 `IMarketDataPort` 的定义位置
- **THEN** MUST 位于 `src/modules/market_insight/domain/ports/market_data_port.py`
- **THEN** 接口返回类型 MUST 使用 `market_insight` 领域层定义的 DTO

### Requirement: DeConceptDataAdapter 实现

系统 MUST 在 `market_insight/infrastructure/adapters/de_concept_data_adapter.py` 中实现 `DeConceptDataAdapter`，实现 `IConceptDataPort` 接口。

该适配器 MUST 通过 `DataEngineeringContainer` 获取 `IConceptRepository` 实例，调用 `get_all_concepts_with_stocks()` 并将 `data_engineering` 的 DTO 转换为 `market_insight` 领域层 DTO。

#### Scenario: 适配器正确转换概念数据

- **WHEN** 调用 `DeConceptDataAdapter.get_all_concepts_with_stocks()`
- **THEN** 返回的 `ConceptWithStocksDTO` 列表 MUST 与 `data_engineering` 中的概念数据一致
- **THEN** DTO 类型 MUST 为 `market_insight` 领域层定义的类型，不包含 `data_engineering` 的类型引用

#### Scenario: data_engineering 无概念数据时返回空列表

- **WHEN** `data_engineering` 的概念表为空
- **THEN** 适配器 MUST 返回空列表 `[]`，不抛出异常

### Requirement: DeMarketDataAdapter 实现

系统 MUST 在 `market_insight/infrastructure/adapters/de_market_data_adapter.py` 中实现 `DeMarketDataAdapter`，实现 `IMarketDataPort` 接口。

该适配器 MUST 调用 `data_engineering` 的 `GetDailyBarsByDateUseCase`（按日期查询全市场日线数据），并将结果转换为 `market_insight` 领域层 DTO。

#### Scenario: 适配器正确转换行情数据

- **WHEN** 调用 `DeMarketDataAdapter.get_daily_bars_by_date(date(2025, 1, 6))`
- **THEN** 返回当日全市场日线数据列表
- **THEN** 每条记录 MUST 为 `StockDailyDTO` 类型

#### Scenario: 指定日期无行情数据

- **WHEN** 调用 `get_daily_bars_by_date()` 且该日期为非交易日
- **THEN** 适配器 MUST 返回空列表 `[]`，不抛出异常

### Requirement: ConceptHeat 领域实体

系统 MUST 在 `market_insight/domain/model/concept_heat.py` 中定义 `ConceptHeat` 实体。

字段 MUST 包含：

- `trade_date`（date）：交易日期
- `concept_code`（str）：概念板块代码
- `concept_name`（str）：概念板块名称
- `avg_pct_chg`（float）：等权平均涨跌幅（百分比）
- `stock_count`（int）：成分股总数
- `up_count`（int）：上涨家数（pct_chg > 0）
- `down_count`（int）：下跌家数（pct_chg < 0）
- `limit_up_count`（int）：涨停家数
- `total_amount`（float）：板块成交额合计

实体 MUST 继承 Pydantic `BaseModel`。

#### Scenario: 实体定义在 Domain 层

- **WHEN** 检查 `ConceptHeat` 的定义位置
- **THEN** MUST 位于 `src/modules/market_insight/domain/model/concept_heat.py`
- **THEN** MUST 继承 Pydantic `BaseModel`

### Requirement: ConceptHeatCalculator 领域服务

系统 MUST 在 `market_insight/domain/services/concept_heat_calculator.py` 中实现 `ConceptHeatCalculator` 领域服务。

该服务 MUST 提供以下方法：

- `calculate(concepts: list[ConceptWithStocksDTO], daily_bars: dict[str, StockDailyDTO]) -> list[ConceptHeat]`

计算逻辑 MUST 遵循：

1. 对每个概念板块，从 `daily_bars`（以 `third_code` 为 key 的字典）中查找其成分股的日线数据。
2. **等权平均涨跌幅**：`avg_pct_chg = sum(成分股 pct_chg) / 有效成分股数量`。仅统计在 `daily_bars` 中存在数据的成分股（忽略停牌股）。
3. 统计 `up_count`（pct_chg > 0）、`down_count`（pct_chg < 0）、`limit_up_count`（符合涨停阈值的成分股数）。
4. 汇总 `total_amount`（成分股成交额之和）。

该服务 MUST 为纯函数式计算，不依赖外部 I/O。

#### Scenario: 正常计算板块热度

- **WHEN** 概念 A 有 5 只成分股，日线数据中 4 只有数据（1 只停牌），涨跌幅分别为 +3.0, +1.5, -0.5, +10.0
- **THEN** `avg_pct_chg` MUST 为 `(3.0 + 1.5 + (-0.5) + 10.0) / 4 = 3.5`
- **THEN** `stock_count` MUST 为 4（有效成分股数）
- **THEN** `up_count` MUST 为 3
- **THEN** `down_count` MUST 为 1

#### Scenario: 概念成分股全部停牌

- **WHEN** 某概念的所有成分股在 `daily_bars` 中均无数据
- **THEN** 该概念 MUST 被排除，不生成 `ConceptHeat` 记录（避免除零错误）

#### Scenario: 涨停成分股被正确统计

- **WHEN** 概念 B 中有 1 只主板股票 pct_chg 为 10.01，1 只创业板股票 pct_chg 为 20.0
- **THEN** 主板股票 MUST 被计入 `limit_up_count`（pct_chg >= 9.9）
- **THEN** 创业板股票 MUST 被计入 `limit_up_count`（pct_chg >= 19.8）

### Requirement: IConceptHeatRepository 持久化接口

系统 MUST 在 `market_insight/domain/ports/repositories/concept_heat_repo.py` 中定义 `IConceptHeatRepository` ABC 接口。

该接口 MUST 包含以下方法：

- `save_all(heats: list[ConceptHeat]) -> int`：批量 UPSERT 概念热度数据（以 trade_date + concept_code 为唯一键），返回影响行数。
- `get_by_date(trade_date: date, top_n: int | None = None) -> list[ConceptHeat]`：查询指定日期的板块热度，按 `avg_pct_chg` 降序排列。若指定 `top_n`，仅返回前 N 条。
- `get_by_concept_and_date_range(concept_code: str, start_date: date, end_date: date) -> list[ConceptHeat]`：查询指定概念在日期范围内的热度历史。

方法 MUST 为异步方法（async）。

#### Scenario: UPSERT 幂等写入

- **WHEN** 对同一 trade_date + concept_code 执行两次 `save_all`
- **THEN** 数据库中仅存在一条记录，字段值为最新值

#### Scenario: 按日期查询热度排名

- **WHEN** 调用 `get_by_date(date(2025, 1, 6), top_n=10)`
- **THEN** 返回该日期前 10 名概念热度数据
- **THEN** 结果 MUST 按 `avg_pct_chg` 降序排列

#### Scenario: 日期无数据时返回空列表

- **WHEN** 调用 `get_by_date()` 且该日期无热度数据
- **THEN** MUST 返回空列表 `[]`

### Requirement: PostgreSQL 持久化实现

系统 MUST 在 `market_insight/infrastructure/persistence/` 下实现概念热度数据的 PostgreSQL 持久化。

包含：

- ORM Model：`ConceptHeatModel`（映射 `mi_concept_heat` 表），位于 `models/concept_heat_model.py`
- Repository 实现：`PgConceptHeatRepository`，实现 `IConceptHeatRepository` 接口，位于 `repositories/pg_concept_heat_repo.py`
- Alembic Migration：创建 `mi_concept_heat` 表

`mi_concept_heat` 表 MUST 包含：`id`（PK）、`trade_date`、`concept_code`、`concept_name`、`avg_pct_chg`、`stock_count`、`up_count`、`down_count`、`limit_up_count`、`total_amount`、`created_at`、`updated_at`。

MUST 在 `(trade_date, concept_code)` 上建立唯一约束。

表名使用 `mi_` 前缀以区分模块归属。

#### Scenario: 数据库表创建

- **WHEN** 运行 Alembic migration
- **THEN** PostgreSQL 中 MUST 存在 `mi_concept_heat` 表
- **THEN** `(trade_date, concept_code)` 唯一约束 MUST 生效

#### Scenario: UPSERT 实现

- **WHEN** 插入与已有记录相同 trade_date + concept_code 的数据
- **THEN** MUST 更新已有记录的 `avg_pct_chg`、`stock_count` 等字段及 `updated_at`

### Requirement: data_engineering 新增按日期批量查询

系统 MUST 在 `data_engineering/application/queries/` 下新增 `GetDailyBarsByDateUseCase`。

接口签名：
```
execute(trade_date: date) -> list[DailyBarDTO]
```

同时 MUST 在 `IMarketQuoteRepository` 中新增方法：
```
get_all_by_trade_date(trade_date: date) -> list[StockDaily]
```

返回指定交易日的全市场日线数据。

#### Scenario: 查询交易日数据

- **WHEN** 调用 `execute(date(2025, 1, 6))`（交易日）
- **THEN** 返回该日全市场日线数据列表
- **THEN** 列表 MUST 不为空

#### Scenario: 查询非交易日数据

- **WHEN** 调用 `execute(date(2025, 1, 4))`（周六）
- **THEN** MUST 返回空列表 `[]`

#### Scenario: DailyBarDTO 包含必要字段

- **WHEN** 查询返回结果
- **THEN** 每条 `DailyBarDTO` MUST 包含 `third_code`、`trade_date`、`open`、`high`、`low`、`close`、`pct_chg`、`vol`、`amount` 字段
