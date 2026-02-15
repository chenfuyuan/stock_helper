# Purpose

定义知识图谱的节点和关系结构，包括股票节点和各维度节点的关系模型。

## Requirements

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

### Requirement: Concept 节点定义

系统 SHALL 在 Neo4j 中维护 `Concept` 标签节点，每个节点代表一个概念题材板块（如"低空经济"、"人形机器人"）。节点 MUST 以 `code` 作为唯一约束键。

节点属性 MUST 包含：

- `code`（String，唯一约束）：概念板块代码（如 `BK0493`）
- `name`（String）：概念板块名称（如 "低空经济"）

#### Scenario: 创建 Concept 节点

- **WHEN** 同步管道写入概念板块 `code = "BK0493"`、`name = "低空经济"`
- **THEN** Neo4j 中 MUST 存在 `(:Concept {code: "BK0493", name: "低空经济"})` 节点

#### Scenario: Concept 节点唯一约束

- **WHEN** 对同一 `code` 执行两次写入（第二次 `name` 有变化）
- **THEN** Neo4j 中仅存在一个该 `code` 的 Concept 节点，`name` 属性为最新一次写入的值

### Requirement: BELONGS_TO_CONCEPT 关系定义

系统 SHALL 在 Stock 节点与 Concept 节点之间创建 `BELONGS_TO_CONCEPT` 关系。方向为 `(Stock)-[:BELONGS_TO_CONCEPT]->(Concept)`。

与 `BELONGS_TO_INDUSTRY` 不同，一个 Stock 节点 MAY 拥有**多条** `BELONGS_TO_CONCEPT` 关系（多对多关系：一股多概念，一概念多股）。

#### Scenario: 建立概念关系

- **WHEN** 股票 `000001.SZ` 属于概念 `BK0493`（低空经济）
- **THEN** MUST 存在 `(:Stock {third_code: "000001.SZ"})-[:BELONGS_TO_CONCEPT]->(:Concept {code: "BK0493"})` 关系

#### Scenario: 一股多概念

- **WHEN** 股票 `000001.SZ` 同时属于 `BK0493`（低空经济）和 `BK0612`（人形机器人）
- **THEN** 该 Stock 节点 MUST 有两条 `BELONGS_TO_CONCEPT` 关系，分别指向两个不同的 Concept 节点

#### Scenario: 概念成份股不存在于图谱时不建关系

- **WHEN** 概念成份股列表中的某个 `third_code` 在 Neo4j 中不存在对应的 Stock 节点
- **THEN** MUST NOT 为该股票创建 `BELONGS_TO_CONCEPT` 关系
- **THEN** 该情况 MUST 被记录到日志（WARNING 级别），包含股票代码和概念名称

### Requirement: 图谱约束初始化

系统 SHALL 在首次连接 Neo4j 或同步前自动创建所有唯一约束：
- `Stock.third_code` UNIQUE
- `Industry.name` UNIQUE
- `Area.name` UNIQUE
- `Market.name` UNIQUE
- `Exchange.name` UNIQUE
- `Concept.code` UNIQUE

#### Scenario: 约束自动创建

- **WHEN** 应用启动并首次连接 Neo4j
- **THEN** 上述 6 个唯一约束 MUST 存在于 Neo4j Schema 中

#### Scenario: Concept 约束自动创建

- **WHEN** 应用启动并执行约束初始化
- **THEN** `Concept.code` 唯一约束 MUST 存在于 Neo4j Schema 中

#### Scenario: 约束已存在时幂等

- **WHEN** 约束初始化逻辑重复执行
- **THEN** 不产生错误，约束保持不变
