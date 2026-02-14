## ADDED Requirements

### Requirement: Stock 节点定义

系统 SHALL 在 Neo4j 中维护 `Stock` 标签节点，每个节点代表一支股票。节点 MUST 以 `third_code` 作为唯一约束键。

节点属性 MUST 包含：
- `third_code`（String，唯一约束）
- `symbol`（String）
- `name`（String）
- `fullname`（String，可为 null）
- `list_date`（String，格式 YYYYMMDD）
- `list_status`（String，枚举：L / D / P）
- `curr_type`（String）

节点属性 MAY 包含以下财务快照字段（来自最新一期财务报表）：
- `roe`、`roa`、`gross_margin`、`debt_to_assets`（盈利与杠杆指标）
- `pe_ttm`、`pb`、`total_mv`（估值指标）

#### Scenario: 创建 Stock 节点

- **WHEN** 同步管道写入一条 `third_code = "000001.SZ"` 的股票数据
- **THEN** Neo4j 中 MUST 存在一个 `(:Stock {third_code: "000001.SZ"})` 节点，包含 `symbol`、`name`、`list_date` 等属性

#### Scenario: Stock 节点唯一约束

- **WHEN** 对同一 `third_code` 执行两次写入
- **THEN** Neo4j 中仅存在一个该 `third_code` 的 Stock 节点，属性为最新一次写入的值

### Requirement: Industry 维度节点定义

系统 SHALL 维护 `Industry` 标签节点，每个节点代表一个行业分类。节点 MUST 以 `name` 作为唯一约束键。

#### Scenario: 创建 Industry 节点

- **WHEN** 同步管道写入行业为"银行"的股票
- **THEN** Neo4j 中 MUST 存在 `(:Industry {name: "银行"})` 节点

#### Scenario: 同行业股票共享同一 Industry 节点

- **WHEN** 两支股票（"000001.SZ" 和 "601398.SH"）均属于"银行"行业
- **THEN** 两个 Stock 节点 MUST 通过关系连接到同一个 `(:Industry {name: "银行"})` 节点

### Requirement: Area 维度节点定义

系统 SHALL 维护 `Area` 标签节点，每个节点代表一个地域。节点 MUST 以 `name` 作为唯一约束键。

#### Scenario: 创建 Area 节点

- **WHEN** 同步管道写入地域为"深圳"的股票
- **THEN** Neo4j 中 MUST 存在 `(:Area {name: "深圳"})` 节点

### Requirement: Market 维度节点定义

系统 SHALL 维护 `Market` 标签节点，每个节点代表一个市场板块（主板、中小板、创业板、科创板等）。节点 MUST 以 `name` 作为唯一约束键。

#### Scenario: 创建 Market 节点

- **WHEN** 同步管道写入市场为"主板"的股票
- **THEN** Neo4j 中 MUST 存在 `(:Market {name: "主板"})` 节点

### Requirement: Exchange 维度节点定义

系统 SHALL 维护 `Exchange` 标签节点，每个节点代表一个交易所（SSE / SZSE 等）。节点 MUST 以 `name` 作为唯一约束键。

#### Scenario: 创建 Exchange 节点

- **WHEN** 同步管道写入交易所为"SSE"的股票
- **THEN** Neo4j 中 MUST 存在 `(:Exchange {name: "SSE"})` 节点

### Requirement: BELONGS_TO_INDUSTRY 关系定义

系统 SHALL 在 Stock 节点与 Industry 节点之间创建 `BELONGS_TO_INDUSTRY` 关系。方向为 `(Stock)-[:BELONGS_TO_INDUSTRY]->(Industry)`。

每个 Stock MUST 最多有一条 `BELONGS_TO_INDUSTRY` 关系。若股票无行业信息（`industry` 为 null 或空），则 MUST NOT 创建该关系。

#### Scenario: 建立行业关系

- **WHEN** 股票 "000001.SZ" 的 `industry` 字段为"银行"
- **THEN** MUST 存在 `(:Stock {third_code: "000001.SZ"})-[:BELONGS_TO_INDUSTRY]->(:Industry {name: "银行"})` 关系

#### Scenario: 行业为空时不建关系

- **WHEN** 某股票的 `industry` 字段为 null
- **THEN** 该 Stock 节点 MUST NOT 存在 `BELONGS_TO_INDUSTRY` 关系

### Requirement: LOCATED_IN 关系定义

系统 SHALL 在 Stock 节点与 Area 节点之间创建 `LOCATED_IN` 关系。方向为 `(Stock)-[:LOCATED_IN]->(Area)`。

每个 Stock MUST 最多有一条 `LOCATED_IN` 关系。

#### Scenario: 建立地域关系

- **WHEN** 股票 "000001.SZ" 的 `area` 字段为"深圳"
- **THEN** MUST 存在 `(:Stock {third_code: "000001.SZ"})-[:LOCATED_IN]->(:Area {name: "深圳"})` 关系

### Requirement: TRADES_ON 关系定义

系统 SHALL 在 Stock 节点与 Market 节点之间创建 `TRADES_ON` 关系。方向为 `(Stock)-[:TRADES_ON]->(Market)`。

#### Scenario: 建立市场关系

- **WHEN** 股票 "000001.SZ" 的 `market` 字段为"主板"
- **THEN** MUST 存在 `(:Stock {third_code: "000001.SZ"})-[:TRADES_ON]->(:Market {name: "主板"})` 关系

### Requirement: LISTED_ON 关系定义

系统 SHALL 在 Stock 节点与 Exchange 节点之间创建 `LISTED_ON` 关系。方向为 `(Stock)-[:LISTED_ON]->(Exchange)`。

#### Scenario: 建立交易所关系

- **WHEN** 股票 "000001.SZ" 的 `exchange` 字段为"SZSE"
- **THEN** MUST 存在 `(:Stock {third_code: "000001.SZ"})-[:LISTED_ON]->(:Exchange {name: "SZSE"})` 关系

### Requirement: 图谱约束初始化

系统 SHALL 在首次连接 Neo4j 或同步前自动创建所有唯一约束：
- `Stock.third_code` UNIQUE
- `Industry.name` UNIQUE
- `Area.name` UNIQUE
- `Market.name` UNIQUE
- `Exchange.name` UNIQUE

#### Scenario: 约束自动创建

- **WHEN** 应用启动并首次连接 Neo4j
- **THEN** 上述 5 个唯一约束 MUST 存在于 Neo4j Schema 中

#### Scenario: 约束已存在时幂等

- **WHEN** 约束初始化逻辑重复执行
- **THEN** 不产生错误，约束保持不变
