# Purpose

`market_insight` 模块提供板块维度的市场洞察分析能力，包含三个核心功能：
- **概念热度计算**：从 `data_engineering` 获取概念成分股映射与日线行情数据，通过等权平均法聚合板块涨跌幅，输出板块热度排名并持久化至 PostgreSQL
- **涨停扫描归因**：识别当日涨停个股，将涨停股映射至所属概念板块，统计各概念涨停家数，并持久化至 PostgreSQL  
- **每日复盘报告**：编排完整计算流程（获取数据 → 计算热度 → 扫描涨停 → 持久化 → 生成报告），输出 Markdown 日报文件，并提供 REST API 端点用于查询和触发

## ADDED Requirements

### 1. 数据获取适配器

#### Requirement: IConceptDataPort 接口定义

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

#### Requirement: IMarketDataPort 接口定义

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

#### Requirement: DeConceptDataAdapter 实现

系统 MUST 在 `market_insight/infrastructure/adapters/de_concept_data_adapter.py` 中实现 `DeConceptDataAdapter`，实现 `IConceptDataPort` 接口。

该适配器 MUST 通过 `DataEngineeringContainer` 获取 `IConceptRepository` 实例，调用 `get_all_concepts_with_stocks()` 并将 `data_engineering` 的 DTO 转换为 `market_insight` 领域层 DTO。

#### Requirement: DeMarketDataAdapter 实现

系统 MUST 在 `market_insight/infrastructure/adapters/de_market_data_adapter.py` 中实现 `DeMarketDataAdapter`，实现 `IMarketDataPort` 接口。

该适配器 MUST 调用 `data_engineering` 的 `GetDailyBarsByDateUseCase`（按日期查询全市场日线数据），并将结果转换为 `market_insight` 领域层 DTO。

### 2. 领域模型与枚举

#### Requirement: Concept 领域实体

系统 MUST 在 `market_insight/domain/model/limit_up_stock.py` 中定义 `Concept` 实体。

字段 MUST 包含：

- `code`（str）：概念板块代码
- `name`（str）：概念板块名称

实体 MUST 继承 Pydantic `BaseModel`。

#### Requirement: ConceptHeat 领域实体

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

#### Requirement: LimitUpStock 领域实体

系统 MUST 在 `market_insight/domain/model/limit_up_stock.py` 中定义 `LimitUpStock` 实体。

字段 MUST 包含：

- `trade_date`（date）：交易日期
- `third_code`（str）：股票代码（系统标准格式，如 `000001.SZ`）
- `stock_name`（str）：股票名称
- `pct_chg`（float）：涨跌幅（百分比）
- `close`（float）：收盘价
- `amount`（float）：成交额
- `concepts`（list[Concept]）：所属概念板块对象列表，每个对象包含 `code` 和 `name` 字段
- `limit_type`（LimitType）：涨停类型枚举

实体 MUST 继承 Pydantic `BaseModel`。

#### Requirement: LimitType 枚举定义

系统 MUST 在 `market_insight/domain/model/enums.py` 中定义 `LimitType` 枚举。

枚举值 MUST 包含：

- `MAIN_BOARD`：主板/中小板涨停（涨跌幅限制 10%）
- `GEM`：创业板涨停（涨跌幅限制 20%）
- `STAR`：科创板涨停（涨跌幅限制 20%）
- `BSE`：北交所涨停（涨跌幅限制 30%）
- `ST`：ST 股票涨停（涨跌幅限制 5%）

### 3. 领域服务

#### Requirement: ConceptHeatCalculator 领域服务

系统 MUST 在 `market_insight/domain/services/concept_heat_calculator.py` 中实现 `ConceptHeatCalculator` 领域服务。

该服务 MUST 提供以下方法：

- `calculate(concepts: list[ConceptWithStocksDTO], daily_bars: dict[str, StockDailyDTO]) -> list[ConceptHeat]`

计算逻辑 MUST 遵循：

1. 对每个概念板块，从 `daily_bars`（以 `third_code` 为 key 的字典）中查找其成分股的日线数据。
2. **等权平均涨跌幅**：`avg_pct_chg = sum(成分股 pct_chg) / 有效成分股数量`。仅统计在 `daily_bars` 中存在数据的成分股（忽略停牌股）。
3. 统计 `up_count`（pct_chg > 0）、`down_count`（pct_chg < 0）、`limit_up_count`（符合涨停阈值的成分股数）。
4. 汇总 `total_amount`（成分股成交额之和）。

该服务 MUST 为纯函数式计算，不依赖外部 I/O。

#### Requirement: LimitUpScanner 领域服务

系统 MUST 在 `market_insight/domain/services/limit_up_scanner.py` 中实现 `LimitUpScanner` 领域服务。

该服务 MUST 提供以下方法：

- `scan(daily_bars: list[StockDailyDTO], concept_stock_map: dict[str, list[ConceptInfoDTO]]) -> list[LimitUpStock]`

涨停判定逻辑 MUST 遵循以下阈值规则：

- 主板/中小板（代码以 `0` 或 `6` 开头，且名称不含 `ST`）：`pct_chg >= 9.9`
- 创业板（代码以 `3` 开头，且名称不含 `ST`）：`pct_chg >= 19.8`
- 科创板（代码以 `68` 开头）：`pct_chg >= 19.8`
- 北交所（代码以 `4` 或 `8` 开头）：`pct_chg >= 29.5`
- ST 股票（名称含 `ST`，不区分大小写）：`pct_chg >= 4.9`

该服务 MUST 为纯函数式计算，不依赖外部 I/O。

### 4. 持久化接口

#### Requirement: IConceptHeatRepository 持久化接口

系统 MUST 在 `market_insight/domain/ports/repositories/concept_heat_repo.py` 中定义 `IConceptHeatRepository` ABC 接口。

该接口 MUST 包含以下方法：

- `save_all(heats: list[ConceptHeat]) -> int`：批量 UPSERT 概念热度数据（以 trade_date + concept_code 为唯一键），返回影响行数。
- `get_by_date(trade_date: date, top_n: int | None = None) -> list[ConceptHeat]`：查询指定日期的板块热度，按 `avg_pct_chg` 降序排列。若指定 `top_n`，仅返回前 N 条。
- `get_by_concept_and_date_range(concept_code: str, start_date: date, end_date: date) -> list[ConceptHeat]`：查询指定概念在日期范围内的热度历史。

方法 MUST 为异步方法（async）。

#### Requirement: ILimitUpRepository 持久化接口

系统 MUST 在 `market_insight/domain/ports/repositories/limit_up_repo.py` 中定义 `ILimitUpRepository` ABC 接口。

该接口 MUST 包含以下方法：

- `save_all(stocks: list[LimitUpStock]) -> int`：批量 UPSERT 涨停股数据（以 trade_date + third_code 为唯一键），返回影响行数。
- `get_by_date(trade_date: date) -> list[LimitUpStock]`：查询指定日期的所有涨停股。
- `get_by_date_and_concept(trade_date: date, concept_code: str) -> list[LimitUpStock]`：查询指定日期、指定概念下的涨停股。

方法 MUST 为异步方法（async）。

### 5. PostgreSQL 持久化实现

#### Requirement: 概念热度数据持久化

系统 MUST 在 `market_insight/infrastructure/persistence/` 下实现概念热度数据的 PostgreSQL 持久化。

包含：

- ORM Model：`ConceptHeatModel`（映射 `mi_concept_heat` 表），位于 `models/concept_heat_model.py`
- Repository 实现：`PgConceptHeatRepository`，实现 `IConceptHeatRepository` 接口，位于 `repositories/pg_concept_heat_repo.py`
- Alembic Migration：创建 `mi_concept_heat` 表

`mi_concept_heat` 表 MUST 包含：`id`（PK）、`trade_date`、`concept_code`、`concept_name`、`avg_pct_chg`、`stock_count`、`up_count`、`down_count`、`limit_up_count`、`total_amount`、`created_at`、`updated_at`。

MUST 在 `(trade_date, concept_code)` 上建立唯一约束。

表名使用 `mi_` 前缀以区分模块归属。

#### Requirement: 涨停股数据持久化

系统 MUST 在 `market_insight/infrastructure/persistence/` 下实现涨停股数据的 PostgreSQL 持久化。

包含：

- ORM Model：`LimitUpStockModel`（映射 `mi_limit_up_stock` 表），位于 `models/limit_up_stock_model.py`
- Repository 实现：`PgLimitUpRepository`，实现 `ILimitUpRepository` 接口，位于 `repositories/pg_limit_up_repo.py`
- Alembic Migration：创建 `mi_limit_up_stock` 表

`mi_limit_up_stock` 表 MUST 包含：`id`（PK）、`trade_date`、`third_code`、`stock_name`、`pct_chg`、`close`、`amount`、`concepts`（JSONB）、`limit_type`、`created_at`、`updated_at`。

MUST 在 `(trade_date, third_code)` 上建立唯一约束。

`concepts` 使用 JSONB 类型存储概念对象数组，每个对象包含 `code` 和 `name` 字段。

表名使用 `mi_` 前缀以区分模块归属。

### 6. 应用层命令与查询

#### Requirement: GenerateDailyReportCmd 应用命令

系统 MUST 在 `market_insight/application/commands/generate_daily_report_cmd.py` 中实现 `GenerateDailyReportCmd`。

该命令 MUST 编排以下完整流程：

1. 通过 `IMarketDataPort` 获取指定日期的全市场日线数据
2. 通过 `IConceptDataPort` 获取所有概念及其成分股映射
3. 构建 `concept_stock_map`（以 third_code 为 key 的反向索引）
4. 调用 `ConceptHeatCalculator.calculate()` 计算板块热度
5. 调用 `LimitUpScanner.scan()` 扫描涨停股
6. 通过 `IConceptHeatRepository.save_all()` 持久化热度数据
7. 通过 `ILimitUpRepository.save_all()` 持久化涨停数据
8. 调用报告生成器输出 Markdown 日报
9. 返回执行结果摘要

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

#### Requirement: GetConceptHeatQuery 查询用例

系统 MUST 在 `market_insight/application/queries/get_concept_heat_query.py` 中实现 `GetConceptHeatQuery`。

接口签名：

```
execute(trade_date: date, top_n: int | None = None) -> list[ConceptHeatDTO]
```

`ConceptHeatDTO` 为 Application 层 DTO，字段 MUST 包含：

- `trade_date`（date）
- `concept_code`（str）
- `concept_name`（str）
- `avg_pct_chg`（float）
- `stock_count`（int）
- `up_count`（int）
- `down_count`（int）
- `limit_up_count`（int）
- `total_amount`（float）

#### Requirement: GetLimitUpQuery 查询用例

系统 MUST 在 `market_insight/application/queries/get_limit_up_query.py` 中实现 `GetLimitUpQuery`。

接口签名：

```
execute(trade_date: date, concept_code: str | None = None) -> list[LimitUpStockDTO]
```

`LimitUpStockDTO` 为 Application 层 DTO，字段 MUST 包含：

- `trade_date`（date）
- `third_code`（str）
- `stock_name`（str）
- `pct_chg`（float）
- `close`（float）
- `amount`（float）
- `concept_codes`（list[str]）：向后兼容属性，从 concepts 对象数组中提取
- `concept_names`（list[str]）：向后兼容属性，从 concepts 对象数组中提取
- `limit_type`（str）

### 7. 报告生成

#### Requirement: MarkdownReportGenerator 报告生成器

系统 MUST 在 `market_insight/infrastructure/report/markdown_report_generator.py` 中实现 `MarkdownReportGenerator`。

该生成器 MUST 根据板块热度和涨停数据生成结构化 Markdown 文件。

输出文件路径格式：`{output_dir}/YYYY-MM-DD-market-insight.md`

报告 MUST 包含以下章节：

1. **标题**：`# 每日市场洞察 - YYYY-MM-DD`
2. **Top N 强势概念**：按 `avg_pct_chg` 降序，以表格形式展示排名、概念名称、涨跌幅、涨停家数、成交额。默认 Top 10。
3. **今日涨停天梯**：按概念分组展示涨停股。每个概念下列出涨停股名称、代码、涨跌幅。
4. **市场概览**：涨停总数、概念板块总数等统计信息。
5. **数据更新时间**：报告生成时间戳。

### 8. REST API 端点

#### Requirement: REST API 端点

系统 MUST 在 `market_insight/presentation/rest/market_insight_router.py` 中实现 FastAPI Router。

Router 前缀 MUST 为 `/api/market-insight`。

MUST 提供以下端点：

| 端点 | 方法 | 参数 | 返回 |
|------|------|------|------|
| `/concept-heat` | GET | `trade_date: date`（必填）、`top_n: int`（可选，默认 10） | `list[ConceptHeatDTO]` |
| `/limit-up` | GET | `trade_date: date`（必填）、`concept_code: str`（可选） | `list[LimitUpStockDTO]` |
| `/daily-report` | POST | `trade_date: date`（必填） | `DailyReportResult` |

所有端点 MUST 使用 Pydantic 响应模型。

### 9. 依赖注入容器

#### Requirement: MarketInsightContainer DI 容器

系统 MUST 在 `market_insight/container.py` 中实现 `MarketInsightContainer`。

该容器 MUST 注册以下依赖：

- `DeConceptDataAdapter` 作为 `IConceptDataPort` 的实现
- `DeMarketDataAdapter` 作为 `IMarketDataPort` 的实现
- `PgConceptHeatRepository` 作为 `IConceptHeatRepository` 的实现
- `PgLimitUpRepository` 作为 `ILimitUpRepository` 的实现
- `ConceptHeatCalculator` 领域服务
- `LimitUpScanner` 领域服务
- `MarkdownReportGenerator` 报告生成器
- `GenerateDailyReportCmd` 应用命令
- `GetConceptHeatQuery` 查询用例
- `GetLimitUpQuery` 查询用例

容器 MUST 接受 `AsyncSession` 和 `DataEngineeringContainer` 作为构造参数。

### 10. 上游模块扩展

#### Requirement: data_engineering 新增按日期批量查询

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

### 11. 架构文档

#### Requirement: vision-and-modules.md 模块注册

系统 MUST 更新 `openspec/specs/vision-and-modules.md` 的模块注册表（第 4.2 节），新增 `market_insight` 模块条目。

| 字段 | 值 |
|------|------|
| 模块 | Market Insight |
| 路径 | `src/modules/market_insight/` |
| 核心职责 | 板块维度的市场洞察分析。概念热度计算、涨停扫描归因、每日复盘报告。 |
| 对外暴露接口 | `GetConceptHeatQuery`, `GetLimitUpQuery`, `GenerateDailyReportCmd` |

同时 MUST 在上下文映射（第 3 节）中体现 `market_insight` 与 `data_engineering` 的依赖关系。

#### Requirement: 调用指南文档

系统 MUST 在 `docs/guides/market-insight-guide.md` 中输出模块调用指南。

文档 MUST 包含以下章节：

1. **模块概述**：功能定位、MVP 能力范围
2. **前置条件**：依赖的数据同步（概念数据、日线行情）及其触发方式
3. **CLI 用法**：命令行触发每日复盘的方式和参数
4. **HTTP API 说明**：各端点的请求/响应示例（含 curl 命令）
5. **输出说明**：Markdown 报告的位置和结构
6. **常见问题**：数据缺失、计算异常等场景的排查指南
