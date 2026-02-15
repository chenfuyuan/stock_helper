# Purpose

`market_insight` 模块的涨停扫描与概念归因能力。识别当日涨停个股，将涨停股映射至所属概念板块，统计各概念涨停家数，并持久化至 PostgreSQL。

## ADDED Requirements

### Requirement: Concept 领域实体

系统 MUST 在 `market_insight/domain/model/limit_up_stock.py` 中定义 `Concept` 实体。

字段 MUST 包含：

- `code`（str）：概念板块代码
- `name`（str）：概念板块名称

实体 MUST 继承 Pydantic `BaseModel`。

### Requirement: LimitUpStock 领域实体

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

#### Scenario: 实体定义在 Domain 层

- **WHEN** 检查 `LimitUpStock` 的定义位置
- **THEN** MUST 位于 `src/modules/market_insight/domain/model/limit_up_stock.py`
- **THEN** MUST 继承 Pydantic `BaseModel`

### Requirement: LimitType 枚举定义

系统 MUST 在 `market_insight/domain/model/enums.py` 中定义 `LimitType` 枚举。

枚举值 MUST 包含：

- `MAIN_BOARD`：主板/中小板涨停（涨跌幅限制 10%）
- `GEM`：创业板涨停（涨跌幅限制 20%）
- `STAR`：科创板涨停（涨跌幅限制 20%）
- `BSE`：北交所涨停（涨跌幅限制 30%）
- `ST`：ST 股票涨停（涨跌幅限制 5%）

#### Scenario: 枚举定义完整

- **WHEN** 检查 `LimitType` 枚举
- **THEN** MUST 包含上述 5 种涨停类型
- **THEN** MUST 位于 `src/modules/market_insight/domain/model/enums.py`

### Requirement: LimitUpScanner 领域服务

系统 MUST 在 `market_insight/domain/services/limit_up_scanner.py` 中实现 `LimitUpScanner` 领域服务。

该服务 MUST 提供以下方法：

- `scan(daily_bars: list[StockDailyDTO], concept_stock_map: dict[str, list[ConceptInfoDTO]]) -> list[LimitUpStock]`

参数说明：
- `daily_bars`：当日全市场日线数据
- `concept_stock_map`：以 `third_code` 为 key、该股票所属概念列表为 value 的映射字典。`ConceptInfoDTO` 字段包含 `code`（str）和 `name`（str）。

涨停判定逻辑 MUST 遵循 Design Decision 4 的阈值规则：

- 主板/中小板（代码以 `0` 或 `6` 开头，且名称不含 `ST`）：`pct_chg >= 9.9`
- 创业板（代码以 `3` 开头，且名称不含 `ST`）：`pct_chg >= 19.8`
- 科创板（代码以 `68` 开头）：`pct_chg >= 19.8`
- 北交所（代码以 `4` 或 `8` 开头）：`pct_chg >= 29.5`
- ST 股票（名称含 `ST`，不区分大小写）：`pct_chg >= 4.9`

该服务 MUST 为纯函数式计算，不依赖外部 I/O。

#### Scenario: 主板股票涨停识别

- **WHEN** 股票代码 `600519.SH`，名称 "贵州茅台"，pct_chg 为 10.01
- **THEN** MUST 被识别为涨停
- **THEN** `limit_type` MUST 为 `LimitType.MAIN_BOARD`

#### Scenario: 创业板股票涨停识别

- **WHEN** 股票代码 `300750.SZ`，名称 "宁德时代"，pct_chg 为 20.0
- **THEN** MUST 被识别为涨停
- **THEN** `limit_type` MUST 为 `LimitType.GEM`

#### Scenario: 科创板股票涨停识别

- **WHEN** 股票代码 `688001.SH`，名称 "华兴源创"，pct_chg 为 19.9
- **THEN** MUST 被识别为涨停
- **THEN** `limit_type` MUST 为 `LimitType.STAR`

#### Scenario: ST 股票涨停识别

- **WHEN** 股票代码 `000007.SZ`，名称 "*ST 全新"，pct_chg 为 5.0
- **THEN** MUST 被识别为涨停
- **THEN** `limit_type` MUST 为 `LimitType.ST`

#### Scenario: 北交所股票涨停识别

- **WHEN** 股票代码 `430047.BJ`，名称 "诺思兰德"，pct_chg 为 30.0
- **THEN** MUST 被识别为涨停
- **THEN** `limit_type` MUST 为 `LimitType.BSE`

#### Scenario: 未达涨停阈值不识别

- **WHEN** 主板股票 pct_chg 为 9.5
- **THEN** MUST 不被识别为涨停

#### Scenario: 涨停股映射概念归因

- **WHEN** 涨停股 `000001.SZ` 属于概念 A（`BK0001`，名称"概念A"）和概念 B（`BK0002`，名称"概念B"）
- **THEN** 返回的 `LimitUpStock` 的 `concepts` MUST 为 `[{"code": "BK0001", "name": "概念A"}, {"code": "BK0002", "name": "概念B"}]`

#### Scenario: 涨停股无概念归属

- **WHEN** 涨停股不在任何概念的成分股中
- **THEN** `concepts` MUST 为空列表 `[]`
- **THEN** 该股仍 MUST 出现在涨停列表中

### Requirement: ILimitUpRepository 持久化接口

系统 MUST 在 `market_insight/domain/ports/repositories/limit_up_repo.py` 中定义 `ILimitUpRepository` ABC 接口。

该接口 MUST 包含以下方法：

- `save_all(stocks: list[LimitUpStock]) -> int`：批量 UPSERT 涨停股数据（以 trade_date + third_code 为唯一键），返回影响行数。
- `get_by_date(trade_date: date) -> list[LimitUpStock]`：查询指定日期的所有涨停股。
- `get_by_date_and_concept(trade_date: date, concept_code: str) -> list[LimitUpStock]`：查询指定日期、指定概念下的涨停股。

方法 MUST 为异步方法（async）。

#### Scenario: UPSERT 幂等写入

- **WHEN** 对同一 trade_date + third_code 执行两次 `save_all`
- **THEN** 数据库中仅存在一条记录，字段值为最新值

#### Scenario: 按日期查询涨停股

- **WHEN** 调用 `get_by_date(date(2025, 1, 6))`
- **THEN** 返回该日全部涨停股列表
- **THEN** 每条记录 MUST 包含完整的概念归因信息

#### Scenario: 按概念过滤涨停股

- **WHEN** 调用 `get_by_date_and_concept(date(2025, 1, 6), "BK0493")`
- **THEN** 仅返回 `concept_codes` 包含 `BK0493` 的涨停股

#### Scenario: 日期无涨停股

- **WHEN** 调用 `get_by_date()` 且该日期无涨停数据
- **THEN** MUST 返回空列表 `[]`

### Requirement: PostgreSQL 持久化实现

系统 MUST 在 `market_insight/infrastructure/persistence/` 下实现涨停股数据的 PostgreSQL 持久化。

包含：

- ORM Model：`LimitUpStockModel`（映射 `mi_limit_up_stock` 表），位于 `models/limit_up_stock_model.py`
- Repository 实现：`PgLimitUpRepository`，实现 `ILimitUpRepository` 接口，位于 `repositories/pg_limit_up_repo.py`
- Alembic Migration：创建 `mi_limit_up_stock` 表

`mi_limit_up_stock` 表 MUST 包含：`id`（PK）、`trade_date`、`third_code`、`stock_name`、`pct_chg`、`close`、`amount`、`concepts`（JSONB）、`limit_type`、`created_at`、`updated_at`。

MUST 在 `(trade_date, third_code)` 上建立唯一约束。

`concepts` 使用 JSONB 类型存储概念对象数组，每个对象包含 `code` 和 `name` 字段。

表名使用 `mi_` 前缀以区分模块归属。

#### Scenario: 数据库表创建

- **WHEN** 运行 Alembic migration
- **THEN** PostgreSQL 中 MUST 存在 `mi_limit_up_stock` 表
- **THEN** `(trade_date, third_code)` 唯一约束 MUST 生效

#### Scenario: JSONB 字段正确存储

- **WHEN** 保存一条涨停股记录，其 `concepts` 为 `[{"code": "BK0001", "name": "概念A"}, {"code": "BK0002", "name": "概念B"}]`
- **THEN** 数据库中 `concepts` 字段 MUST 以 JSONB 格式存储概念对象数组
- **THEN** 查询时 MUST 还原为 `list[Concept]`

#### Scenario: 按概念过滤使用 JSONB 查询

- **WHEN** 调用 `get_by_date_and_concept()` 过滤特定概念
- **THEN** MUST 使用 PostgreSQL JSONB 包含查询（如 `concepts @> '[{"code": "BK0493"}]'`）
