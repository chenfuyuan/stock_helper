## ADDED Requirements

### Requirement: AkShare 基类提取

系统 MUST 在 `data_engineering/infrastructure/external_apis/akshare/base_client.py` 中定义 `AkShareBaseClient` 基类，封装 AkShare API 调用的通用逻辑。

基类 MUST 提供以下能力：
- `_run_in_executor(func, *args, **kwargs)`: 在线程池中执行同步 AkShare API 调用，避免阻塞事件循环
- `_rate_limited_call(func, *args, **kwargs)`: 带进程级限速的 API 调用，使用全局共享锁控制调用频率
- `request_interval`（可配置，默认 0.3s）

现有 `AkShareConceptClient` MUST 重构为继承 `AkShareBaseClient`，移除重复的限速和异步执行代码。

#### Scenario: 基类限速逻辑复用

- **WHEN** `AkShareMarketDataClient` 和 `AkShareConceptClient` 同时发起 API 调用
- **THEN** 两者 MUST 共享同一个进程级限速锁，调用间隔不小于 `request_interval`

#### Scenario: 现有功能不受影响

- **WHEN** `AkShareConceptClient` 重构为继承 `AkShareBaseClient` 后
- **THEN** `fetch_concept_list()` 和 `fetch_concept_constituents()` 的行为 MUST 与重构前完全一致

---

### Requirement: IMarketSentimentProvider 接口定义

系统 MUST 在 `data_engineering/domain/ports/providers/market_sentiment_provider.py` 中定义 `IMarketSentimentProvider` ABC 接口，用于获取市场情绪相关数据。

该接口 MUST 包含以下方法：

- `fetch_limit_up_pool(trade_date: date) -> list[LimitUpPoolDTO]`：获取指定日期的涨停池数据（含连板天数）
- `fetch_broken_board_pool(trade_date: date) -> list[BrokenBoardDTO]`：获取指定日期的炸板池数据
- `fetch_previous_limit_up(trade_date: date) -> list[PreviousLimitUpDTO]`：获取昨日涨停股今日表现数据

所有方法 MUST 为异步方法（async）。

`LimitUpPoolDTO` 字段 MUST 包含：
- `third_code`（str）：股票代码（系统标准格式，如 `000001.SZ`）
- `stock_name`（str）：股票名称
- `pct_chg`（float）：涨跌幅（百分比）
- `close`（float）：最新价
- `amount`（float）：成交额
- `turnover_rate`（float）：换手率
- `consecutive_boards`（int）：连板天数（首板为 1）
- `first_limit_up_time`（str | None）：首次封板时间
- `last_limit_up_time`（str | None）：最后封板时间
- `industry`（str）：所属行业

`BrokenBoardDTO` 字段 MUST 包含：
- `third_code`（str）：股票代码
- `stock_name`（str）：股票名称
- `pct_chg`（float）：涨跌幅
- `close`（float）：最新价
- `amount`（float）：成交额
- `turnover_rate`（float）：换手率
- `open_count`（int）：开板次数
- `first_limit_up_time`（str | None）：首次封板时间
- `last_open_time`（str | None）：最后开板时间
- `industry`（str）：所属行业

`PreviousLimitUpDTO` 字段 MUST 包含：
- `third_code`（str）：股票代码
- `stock_name`（str）：股票名称
- `pct_chg`（float）：今日涨跌幅
- `close`（float）：最新价
- `amount`（float）：成交额
- `turnover_rate`（float）：换手率
- `yesterday_consecutive_boards`（int）：昨日连板天数
- `industry`（str）：所属行业

所有 DTO MUST 定义在 `data_engineering/domain/dtos/market_sentiment_dtos.py` 中。

#### Scenario: Port 在 Domain 层定义

- **WHEN** 检查 `IMarketSentimentProvider` 的定义位置
- **THEN** MUST 位于 `data_engineering/domain/ports/providers/market_sentiment_provider.py`
- **THEN** 返回类型 MUST 使用 `data_engineering` 领域层定义的 DTO

---

### Requirement: IDragonTigerProvider 接口定义

系统 MUST 在 `data_engineering/domain/ports/providers/dragon_tiger_provider.py` 中定义 `IDragonTigerProvider` ABC 接口。

该接口 MUST 包含以下方法：

- `fetch_dragon_tiger_detail(trade_date: date) -> list[DragonTigerDetailDTO]`：获取指定日期的龙虎榜详情数据

方法 MUST 为异步方法（async）。

`DragonTigerDetailDTO` 字段 MUST 包含：
- `third_code`（str）：股票代码
- `stock_name`（str）：股票名称
- `pct_chg`（float）：涨跌幅
- `close`（float）：收盘价
- `reason`（str）：上榜原因
- `net_amount`（float）：龙虎榜净买入额
- `buy_amount`（float）：买入总额
- `sell_amount`（float）：卖出总额
- `buy_seats`（list[dict]）：买入席位详情列表，每项包含 `seat_name`（str）和 `buy_amount`（float）
- `sell_seats`（list[dict]）：卖出席位详情列表，每项包含 `seat_name`（str）和 `sell_amount`（float）

DTO MUST 定义在 `data_engineering/domain/dtos/dragon_tiger_dtos.py` 中。

#### Scenario: Port 在 Domain 层定义

- **WHEN** 检查 `IDragonTigerProvider` 的定义位置
- **THEN** MUST 位于 `data_engineering/domain/ports/providers/dragon_tiger_provider.py`

---

### Requirement: ISectorCapitalFlowProvider 接口定义

系统 MUST 在 `data_engineering/domain/ports/providers/sector_capital_flow_provider.py` 中定义 `ISectorCapitalFlowProvider` ABC 接口。

该接口 MUST 包含以下方法：

- `fetch_sector_capital_flow(sector_type: str = "概念资金流") -> list[SectorCapitalFlowDTO]`：获取当日板块资金流向排名

方法 MUST 为异步方法（async）。

`SectorCapitalFlowDTO` 字段 MUST 包含：
- `sector_name`（str）：板块名称
- `sector_type`（str）：板块类型（如"概念资金流"）
- `net_amount`（float）：净流入额（万元）
- `inflow_amount`（float）：流入额（万元）
- `outflow_amount`（float）：流出额（万元）
- `pct_chg`（float）：板块涨跌幅

DTO MUST 定义在 `data_engineering/domain/dtos/capital_flow_dtos.py` 中。

#### Scenario: Port 在 Domain 层定义

- **WHEN** 检查 `ISectorCapitalFlowProvider` 的定义位置
- **THEN** MUST 位于 `data_engineering/domain/ports/providers/sector_capital_flow_provider.py`

---

### Requirement: AkShareMarketDataClient 适配器实现

系统 MUST 在 `data_engineering/infrastructure/external_apis/akshare/market_data_client.py` 中实现 `AkShareMarketDataClient`，继承 `AkShareBaseClient`，并实现 `IMarketSentimentProvider`、`IDragonTigerProvider`、`ISectorCapitalFlowProvider` 三个接口。

该客户端 MUST 调用以下 AkShare API：
- 涨停池：`ak.stock_zt_pool_em(date=<yyyymmdd>)`
- 炸板池：`ak.stock_zt_pool_zbgc_em(date=<yyyymmdd>)`
- 昨日涨停表现：`ak.stock_zt_pool_previous_em(date=<yyyymmdd>)`
- 龙虎榜详情：`ak.stock_lhb_detail_em(start_date=<yyyymmdd>, end_date=<yyyymmdd>)`
- 板块资金流向：`ak.stock_sector_fund_flow_rank(indicator="今日", sector_type=<type>)`

股票代码 MUST 使用 `stock_code_converter` 转换为系统标准格式。

每个 `fetch_*` 方法 MUST：
1. 通过 `_rate_limited_call` 执行 API 调用
2. 处理空返回（返回空列表，记录 WARNING 日志）
3. 捕获 `ImportError` 抛出 `AppException(code="AKSHARE_IMPORT_ERROR")`
4. 捕获其他异常抛出 `AppException(code="AKSHARE_API_ERROR")`

#### Scenario: 正常获取涨停池数据

- **WHEN** 调用 `fetch_limit_up_pool(date(2024, 2, 15))`，AkShare API 返回有效数据
- **THEN** 系统 MUST 返回 `list[LimitUpPoolDTO]`，股票代码为系统标准格式，`consecutive_boards` 正确解析

#### Scenario: API 返回空数据

- **WHEN** 调用 `fetch_limit_up_pool(date(2024, 2, 15))`，AkShare 返回空 DataFrame
- **THEN** 系统 MUST 返回空列表并记录 WARNING 日志

#### Scenario: AkShare 未安装

- **WHEN** 调用任意 `fetch_*` 方法但 `akshare` 库未安装
- **THEN** 系统 MUST 抛出 `AppException(code="AKSHARE_IMPORT_ERROR")`

#### Scenario: API 调用失败

- **WHEN** 调用任意 `fetch_*` 方法时 AkShare API 抛出异常
- **THEN** 系统 MUST 抛出 `AppException(code="AKSHARE_API_ERROR")`，details 包含原始错误信息

---

### Requirement: 涨停池数据领域实体与持久化

系统 MUST 在 `data_engineering/domain/model/limit_up_pool.py` 中定义 `LimitUpPoolStock` 领域实体（继承 Pydantic `BaseModel`）。

字段 MUST 包含：
- `trade_date`（date）：交易日期
- `third_code`（str）：股票代码
- `stock_name`（str）：股票名称
- `pct_chg`（float）：涨跌幅
- `close`（float）：最新价
- `amount`（float）：成交额
- `turnover_rate`（float）：换手率
- `consecutive_boards`（int）：连板天数
- `first_limit_up_time`（str | None）：首次封板时间
- `last_limit_up_time`（str | None）：最后封板时间
- `industry`（str）：所属行业

系统 MUST 在 `data_engineering/domain/ports/repositories/limit_up_pool_repo.py` 中定义 `ILimitUpPoolRepository` ABC 接口，包含：
- `save_all(stocks: list[LimitUpPoolStock]) -> int`：批量 UPSERT，以 `(trade_date, third_code)` 为唯一键
- `get_by_date(trade_date: date) -> list[LimitUpPoolStock]`：查询指定日期涨停池

系统 MUST 在 `data_engineering/infrastructure/persistence/` 下实现 PostgreSQL 持久化：
- ORM Model：`LimitUpPoolModel` 映射 `de_limit_up_pool` 表
- Repository：`PgLimitUpPoolRepository` 实现 `ILimitUpPoolRepository`
- Alembic Migration：创建 `de_limit_up_pool` 表，`(trade_date, third_code)` 唯一约束

#### Scenario: 批量 UPSERT 涨停池数据

- **WHEN** 调用 `save_all` 传入 10 条涨停池数据，其中 3 条与已有记录键冲突
- **THEN** 系统 MUST 插入 7 条新记录并更新 3 条已有记录，返回影响行数 10

#### Scenario: 按日期查询涨停池

- **WHEN** 调用 `get_by_date(date(2024, 2, 15))`
- **THEN** 系统 MUST 返回该日期的所有涨停池记录

---

### Requirement: 炸板池数据领域实体与持久化

系统 MUST 在 `data_engineering/domain/model/broken_board.py` 中定义 `BrokenBoardStock` 领域实体（继承 Pydantic `BaseModel`）。

字段 MUST 包含：
- `trade_date`（date）：交易日期
- `third_code`（str）：股票代码
- `stock_name`（str）：股票名称
- `pct_chg`（float）：涨跌幅
- `close`（float）：最新价
- `amount`（float）：成交额
- `turnover_rate`（float）：换手率
- `open_count`（int）：开板次数
- `first_limit_up_time`（str | None）：首次封板时间
- `last_open_time`（str | None）：最后开板时间
- `industry`（str）：所属行业

系统 MUST 在 `data_engineering/domain/ports/repositories/broken_board_repo.py` 中定义 `IBrokenBoardRepository` ABC 接口，包含：
- `save_all(stocks: list[BrokenBoardStock]) -> int`：批量 UPSERT，以 `(trade_date, third_code)` 为唯一键
- `get_by_date(trade_date: date) -> list[BrokenBoardStock]`：查询指定日期炸板池

系统 MUST 实现对应的 ORM Model（`BrokenBoardModel` → `de_broken_board_pool` 表）和 PostgreSQL Repository。

#### Scenario: 批量 UPSERT 炸板池数据

- **WHEN** 调用 `save_all` 传入炸板池数据
- **THEN** 系统 MUST 以 `(trade_date, third_code)` 为唯一键执行 UPSERT

#### Scenario: 按日期查询炸板池

- **WHEN** 调用 `get_by_date(date(2024, 2, 15))`
- **THEN** 系统 MUST 返回该日期的所有炸板池记录

---

### Requirement: 昨日涨停表现数据领域实体与持久化

系统 MUST 在 `data_engineering/domain/model/previous_limit_up.py` 中定义 `PreviousLimitUpStock` 领域实体（继承 Pydantic `BaseModel`）。

字段 MUST 包含：
- `trade_date`（date）：交易日期（今日日期，即表现观察日）
- `third_code`（str）：股票代码
- `stock_name`（str）：股票名称
- `pct_chg`（float）：今日涨跌幅
- `close`（float）：最新价
- `amount`（float）：成交额
- `turnover_rate`（float）：换手率
- `yesterday_consecutive_boards`（int）：昨日连板天数
- `industry`（str）：所属行业

系统 MUST 定义 `IPreviousLimitUpRepository` 接口（含 `save_all`、`get_by_date`）并实现 PostgreSQL 持久化（`de_previous_limit_up` 表，`(trade_date, third_code)` 唯一约束）。

#### Scenario: 批量 UPSERT 昨日涨停表现

- **WHEN** 调用 `save_all` 传入昨日涨停表现数据
- **THEN** 系统 MUST 以 `(trade_date, third_code)` 为唯一键执行 UPSERT

#### Scenario: 按日期查询昨日涨停表现

- **WHEN** 调用 `get_by_date(date(2024, 2, 15))`
- **THEN** 系统 MUST 返回该日期的所有昨日涨停表现记录

---

### Requirement: 龙虎榜数据领域实体与持久化

系统 MUST 在 `data_engineering/domain/model/dragon_tiger.py` 中定义 `DragonTigerDetail` 领域实体（继承 Pydantic `BaseModel`）。

字段 MUST 包含：
- `trade_date`（date）：交易日期
- `third_code`（str）：股票代码
- `stock_name`（str）：股票名称
- `pct_chg`（float）：涨跌幅
- `close`（float）：收盘价
- `reason`（str）：上榜原因
- `net_amount`（float）：龙虎榜净买入额
- `buy_amount`（float）：买入总额
- `sell_amount`（float）：卖出总额
- `buy_seats`（list[dict]）：买入席位详情（JSONB 存储）
- `sell_seats`（list[dict]）：卖出席位详情（JSONB 存储）

系统 MUST 定义 `IDragonTigerRepository` 接口，包含：
- `save_all(details: list[DragonTigerDetail]) -> int`：批量 UPSERT，以 `(trade_date, third_code, reason)` 为唯一键
- `get_by_date(trade_date: date) -> list[DragonTigerDetail]`：查询指定日期龙虎榜

系统 MUST 实现 ORM Model（`DragonTigerModel` → `de_dragon_tiger` 表）和 PostgreSQL Repository。`buy_seats` 和 `sell_seats` MUST 使用 JSONB 类型存储。

#### Scenario: 批量 UPSERT 龙虎榜数据

- **WHEN** 调用 `save_all` 传入龙虎榜数据，其中同一股票可因不同上榜原因有多条记录
- **THEN** 系统 MUST 以 `(trade_date, third_code, reason)` 为唯一键执行 UPSERT

#### Scenario: 按日期查询龙虎榜

- **WHEN** 调用 `get_by_date(date(2024, 2, 15))`
- **THEN** 系统 MUST 返回该日期的所有龙虎榜记录，含席位详情

---

### Requirement: 板块资金流向数据领域实体与持久化

系统 MUST 在 `data_engineering/domain/model/sector_capital_flow.py` 中定义 `SectorCapitalFlow` 领域实体（继承 Pydantic `BaseModel`）。

字段 MUST 包含：
- `trade_date`（date）：交易日期
- `sector_name`（str）：板块名称
- `sector_type`（str）：板块类型（如"概念资金流"）
- `net_amount`（float）：净流入额（万元）
- `inflow_amount`（float）：流入额（万元）
- `outflow_amount`（float）：流出额（万元）
- `pct_chg`（float）：板块涨跌幅

系统 MUST 定义 `ISectorCapitalFlowRepository` 接口，包含：
- `save_all(flows: list[SectorCapitalFlow]) -> int`：批量 UPSERT，以 `(trade_date, sector_name, sector_type)` 为唯一键
- `get_by_date(trade_date: date, sector_type: str | None = None) -> list[SectorCapitalFlow]`：查询指定日期板块资金流向

系统 MUST 实现 ORM Model（`SectorCapitalFlowModel` → `de_sector_capital_flow` 表）和 PostgreSQL Repository。

#### Scenario: 批量 UPSERT 板块资金流向

- **WHEN** 调用 `save_all` 传入板块资金流向数据
- **THEN** 系统 MUST 以 `(trade_date, sector_name, sector_type)` 为唯一键执行 UPSERT

#### Scenario: 按日期查询板块资金流向

- **WHEN** 调用 `get_by_date(date(2024, 2, 15))`
- **THEN** 系统 MUST 返回该日期的所有板块资金流向记录

#### Scenario: 按日期和板块类型过滤

- **WHEN** 调用 `get_by_date(date(2024, 2, 15), sector_type="概念资金流")`
- **THEN** 系统 MUST 仅返回"概念资金流"类型的记录

---

### Requirement: SyncAkShareMarketDataCmd 同步命令

系统 MUST 在 `data_engineering/application/commands/sync_akshare_market_data_cmd.py` 中实现 `SyncAkShareMarketDataCmd` 应用命令。

该命令 MUST 编排以下同步流程：

1. 通过 `IMarketSentimentProvider` 获取涨停池、炸板池、昨日涨停表现
2. 通过 `IDragonTigerProvider` 获取龙虎榜详情
3. 通过 `ISectorCapitalFlowProvider` 获取板块资金流向
4. 将 DTO 转换为领域实体
5. 通过对应 Repository 批量 UPSERT 持久化

接口签名：
```
execute(trade_date: date) -> AkShareSyncResult
```

`AkShareSyncResult` 为 Application 层 DTO，字段 MUST 包含：
- `trade_date`（date）
- `limit_up_pool_count`（int）：涨停池记录数
- `broken_board_count`（int）：炸板池记录数
- `previous_limit_up_count`（int）：昨日涨停表现记录数
- `dragon_tiger_count`（int）：龙虎榜记录数
- `sector_capital_flow_count`（int）：板块资金流向记录数
- `errors`（list[str]）：各类数据同步失败的错误信息列表

单类数据采集失败 MUST NOT 中断其他类型的同步，错误信息记录到 `errors` 列表并记录 ERROR 日志。

#### Scenario: 正常全量同步

- **WHEN** 调用 `execute(date(2024, 2, 15))`，所有 AkShare API 正常返回
- **THEN** 系统 MUST 依次采集 5 类数据并持久化，返回各类记录数，`errors` 为空列表

#### Scenario: 部分数据采集失败

- **WHEN** 调用 `execute(date(2024, 2, 15))`，龙虎榜 API 调用失败但其余正常
- **THEN** 系统 MUST 持久化其余 4 类数据，`dragon_tiger_count` 为 0，`errors` 包含龙虎榜的错误信息

#### Scenario: 幂等同步

- **WHEN** 对同一 `trade_date` 连续调用两次 `execute`
- **THEN** 第二次调用 MUST 通过 UPSERT 更新已有记录，不产生重复数据

---

### Requirement: AkShare 数据查询用例

系统 MUST 在 `data_engineering/application/queries/` 下提供以下查询用例，供 `market_insight` 模块通过 Ports 消费：

1. `GetLimitUpPoolByDateUseCase`：
   - 签名：`execute(trade_date: date) -> list[LimitUpPoolStock]`
   - 位置：`get_limit_up_pool_by_date.py`

2. `GetBrokenBoardByDateUseCase`：
   - 签名：`execute(trade_date: date) -> list[BrokenBoardStock]`
   - 位置：`get_broken_board_by_date.py`

3. `GetPreviousLimitUpByDateUseCase`：
   - 签名：`execute(trade_date: date) -> list[PreviousLimitUpStock]`
   - 位置：`get_previous_limit_up_by_date.py`

4. `GetDragonTigerByDateUseCase`：
   - 签名：`execute(trade_date: date) -> list[DragonTigerDetail]`
   - 位置：`get_dragon_tiger_by_date.py`

5. `GetSectorCapitalFlowByDateUseCase`：
   - 签名：`execute(trade_date: date, sector_type: str | None = None) -> list[SectorCapitalFlow]`
   - 位置：`get_sector_capital_flow_by_date.py`

每个查询用例 MUST 通过对应的 Repository Port 查询数据。

#### Scenario: 查询涨停池

- **WHEN** 调用 `GetLimitUpPoolByDateUseCase.execute(date(2024, 2, 15))`
- **THEN** 系统 MUST 通过 `ILimitUpPoolRepository.get_by_date` 返回该日期涨停池数据

#### Scenario: 查询龙虎榜

- **WHEN** 调用 `GetDragonTigerByDateUseCase.execute(date(2024, 2, 15))`
- **THEN** 系统 MUST 通过 `IDragonTigerRepository.get_by_date` 返回该日期龙虎榜数据

---

### Requirement: DI 容器扩展

系统 MUST 更新 `data_engineering/container.py` 的 `DataEngineeringContainer`，注册以下新增依赖：

- `AkShareMarketDataClient` 实例（实现 `IMarketSentimentProvider`、`IDragonTigerProvider`、`ISectorCapitalFlowProvider`）
- `PgLimitUpPoolRepository`、`PgBrokenBoardRepository`、`PgPreviousLimitUpRepository`、`PgDragonTigerRepository`、`PgSectorCapitalFlowRepository`
- `SyncAkShareMarketDataCmd`
- 各查询用例（`GetLimitUpPoolByDateUseCase` 等）

容器 MUST 提供工厂方法用于获取：
- `get_sync_akshare_market_data_cmd() -> SyncAkShareMarketDataCmd`
- `get_limit_up_pool_by_date_use_case() -> GetLimitUpPoolByDateUseCase`
- `get_broken_board_by_date_use_case() -> GetBrokenBoardByDateUseCase`
- `get_previous_limit_up_by_date_use_case() -> GetPreviousLimitUpByDateUseCase`
- `get_dragon_tiger_by_date_use_case() -> GetDragonTigerByDateUseCase`
- `get_sector_capital_flow_by_date_use_case() -> GetSectorCapitalFlowByDateUseCase`

#### Scenario: 容器注册完整性

- **WHEN** 通过 `DataEngineeringContainer` 获取 `SyncAkShareMarketDataCmd`
- **THEN** 系统 MUST 返回正确装配的实例，内部注入了所有 Provider 和 Repository 依赖
