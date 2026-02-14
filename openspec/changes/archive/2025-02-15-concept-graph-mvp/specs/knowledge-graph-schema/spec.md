# Purpose

扩展知识图谱 Schema，新增概念题材节点和关系定义。

## ADDED Requirements

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

### Requirement: Concept 唯一约束初始化

系统 SHALL 在图谱约束初始化时（`ensure_constraints`）额外创建 `Concept.code` 的唯一约束。

#### Scenario: Concept 约束自动创建

- **WHEN** 应用启动并执行约束初始化
- **THEN** `Concept.code` 唯一约束 MUST 存在于 Neo4j Schema 中

#### Scenario: 约束已存在时幂等

- **WHEN** 约束初始化逻辑重复执行
- **THEN** 不产生错误，约束保持不变
