# Purpose

提供从数据工程模块到知识图谱的数据同步能力，支持全量和增量同步策略。

## Requirements

### Requirement: 全量同步命令

系统 SHALL 提供全量同步命令（`SyncGraphCommand`，mode=full），从 `data_engineering` 模块读取所有 StockInfo 数据并写入 Neo4j 图谱。

全量同步 MUST 包含以下步骤：
1. 通过 `data_engineering` 的 Port 查询所有股票基本信息。
2. 通过 Adapter 将跨模块 DTO 转换为本模块 `GraphSyncDTO`。
3. 调用 `GraphRepository` 批量写入 Stock 节点、维度节点及关系。
4. 可选同步最新财务快照（通过 `FinancialRepo` Port）。

#### Scenario: 首次全量同步

- **WHEN** 用户触发全量同步命令且 Neo4j 图谱为空
- **THEN** 系统从 PostgreSQL 读取所有 StockInfo 记录，在 Neo4j 中为每条记录创建 Stock 节点及对应维度节点和关系
- **THEN** 同步完成后 Neo4j 中 Stock 节点总数 MUST 等于 PostgreSQL `stock_info` 表中的记录数

#### Scenario: 重复全量同步幂等

- **WHEN** 对已存在数据的图谱执行全量同步
- **THEN** 使用 Cypher MERGE 确保节点和关系不重复，属性更新为最新值
- **THEN** 同步前后 Stock 节点总数保持不变（除非源数据有增减）

### Requirement: 增量同步命令

系统 SHALL 提供增量同步命令（`SyncGraphCommand`，mode=incremental），仅同步指定范围的股票数据。

增量同步 MUST 支持以下过滤方式（至少一种）：
- 指定 `third_codes` 列表：仅同步指定股票。
- 指定时间窗口：同步在该时间窗口内有数据变更的股票。

#### Scenario: 按股票代码增量同步

- **WHEN** 用户触发增量同步，指定 `third_codes = ["000001.SZ", "601398.SH"]`
- **THEN** 系统仅查询并同步这两支股票的数据到 Neo4j
- **THEN** 其他股票的图谱数据保持不变

#### Scenario: 增量同步新增股票

- **WHEN** PostgreSQL 中新增了一支股票 "688001.SH"，触发增量同步包含该股票
- **THEN** Neo4j 中 MUST 新增该 Stock 节点及对应维度关系

### Requirement: 批量写入性能

同步管道 MUST 使用批量写入策略（Cypher UNWIND + MERGE），避免逐条事务提交。

每批提交的记录数 SHALL 可配置，默认值为 500。

#### Scenario: 批量写入执行

- **WHEN** 同步 5000 条股票数据，批量大小为 500
- **THEN** 系统 MUST 分 10 批提交，每批包含约 500 条 MERGE 操作
- **THEN** 不 SHALL 出现单条逐一提交的情况

### Requirement: 财务快照同步

同步管道 SHALL 支持将最新一期财务报表数据同步为 Stock 节点的属性。

同步的财务字段 MUST 包含：`roe`、`roa`、`gross_margin`、`debt_to_assets`、`pe_ttm`、`pb`、`total_mv`。

#### Scenario: 同步财务快照

- **WHEN** 全量同步包含财务数据
- **THEN** Stock 节点的财务属性 MUST 反映该股票最新一期（`end_date` 最大）的财务数据

#### Scenario: 无财务数据时属性为 null

- **WHEN** 某股票在 PostgreSQL 中无财务报表记录
- **THEN** 该 Stock 节点的财务属性 MUST 为 null（不设默认值）

### Requirement: 跨模块数据读取通过 Adapter

同步管道从 `data_engineering` 读取数据 MUST 通过 `knowledge_center/infrastructure/adapters/data_engineering_adapter.py` 完成。

Adapter MUST 将 `data_engineering` 的 DTO 转换为本模块 `domain/dtos/graph_sync_dtos.py` 中定义的 DTO。Domain 层 MUST NOT import `data_engineering` 的任何类型。

#### Scenario: Adapter 数据转换

- **WHEN** Adapter 从 `data_engineering` 获取 StockInfo 数据
- **THEN** 返回的 DTO 类型 MUST 属于 `knowledge_center.domain.dtos` 包
- **THEN** 不包含对 `data_engineering` 模块类型的直接引用

### Requirement: 同步错误处理

同步管道 MUST 对单条记录的写入失败进行容错处理，不 SHALL 因个别记录失败而中断整个同步流程。

失败记录 MUST 被记录到日志中（包含 `third_code` 和错误信息），日志级别为 ERROR。

#### Scenario: 单条记录失败不中断同步

- **WHEN** 同步过程中某一条股票数据因属性格式异常导致写入 Neo4j 失败
- **THEN** 该记录的错误信息 MUST 被记录到日志
- **THEN** 其余记录的同步 MUST 正常继续

#### Scenario: 同步完成后报告结果

- **WHEN** 同步命令执行完毕
- **THEN** MUST 返回同步结果摘要，包含：成功数量、失败数量、总耗时

### Requirement: 概念数据全量同步命令

系统 SHALL 提供概念图谱全量同步命令（`SyncConceptGraphCmd`），从 `data_engineering` 的 PostgreSQL（通过适配器）读取概念板块数据并写入 Neo4j 图谱。

前置条件：概念数据已通过 DE 模块的 `SyncConceptDataCmd` 同步到 PostgreSQL。

同步 MUST 包含以下步骤：

1. 通过 KC 适配器调用 DE 的 `IConceptRepository.get_all_concepts_with_stocks()` 获取所有概念及成份股
2. 删除 Neo4j 中所有现有的 `BELONGS_TO_CONCEPT` 关系（先清策略）
3. 批量 MERGE Concept 节点（by code）
4. 批量创建 `(Stock)-[:BELONGS_TO_CONCEPT]->(Concept)` 关系（仅当 Stock 节点已存在时）

#### Scenario: 首次概念图谱同步

- **WHEN** 用户触发概念图谱同步且 Neo4j 中无 Concept 节点
- **THEN** 系统从 DE 的 PostgreSQL 读取所有概念板块及成份股
- **THEN** Neo4j 中 MUST 创建对应的 Concept 节点和 BELONGS_TO_CONCEPT 关系

#### Scenario: 重复概念同步保持一致

- **WHEN** 对已存在概念数据的图谱再次执行全量同步
- **THEN** 旧的 BELONGS_TO_CONCEPT 关系 MUST 先被全部删除
- **THEN** 基于 PostgreSQL 中的最新数据重建所有 Concept 节点（MERGE）和关系
- **THEN** 若某股票已从某概念中移除，新图谱中 MUST NOT 存在该陈旧关系

#### Scenario: PostgreSQL 无概念数据时

- **WHEN** 触发概念图谱同步但 DE 的 PostgreSQL 中无概念数据
- **THEN** 同步命令 MUST 记录 WARNING 日志并返回空结果（概念总数 = 0），不抛出异常

#### Scenario: 同步完成后报告结果

- **WHEN** 概念同步命令执行完毕
- **THEN** MUST 返回同步结果摘要，包含：概念总数、Concept 节点数、创建的关系总数、总耗时

### Requirement: 概念同步的批量写入

概念同步管道 MUST 使用批量写入策略，避免逐条事务提交。

- Concept 节点 MUST 使用 Cypher `UNWIND + MERGE` 批量写入
- BELONGS_TO_CONCEPT 关系 MUST 使用 Cypher `UNWIND + MATCH + MERGE` 批量写入（MATCH Stock 节点，仅当存在时创建关系）

#### Scenario: 批量写入概念节点

- **WHEN** 同步 300 个概念板块
- **THEN** 系统 MUST 使用批量操作写入，不 SHALL 逐条提交

#### Scenario: 批量写入概念关系

- **WHEN** 某概念有 50 个成份股
- **THEN** 系统 MUST 通过 UNWIND 一次性写入该概念的所有 Stock-Concept 关系

### Requirement: 跨模块概念数据读取通过 Adapter

`knowledge_center` 从 `data_engineering` 获取概念数据 MUST 通过 `knowledge_center/infrastructure/adapters/` 下的适配器完成。

适配器 MUST 注入 DE 的 `IConceptRepository`（或 DE 暴露的应用服务），调用 `get_all_concepts_with_stocks()` 查询 PostgreSQL 中的概念数据。

适配器 MUST 将 `data_engineering` 的 DTO（`ConceptWithStocksDTO`）转换为 `knowledge_center` 的 `domain/dtos/` 中定义的同步 DTO（`ConceptGraphSyncDTO`）。`knowledge_center` 的 Domain 层 MUST NOT import `data_engineering` 的任何类型。

#### Scenario: Adapter 从 PostgreSQL 读取数据

- **WHEN** Adapter 被调用获取概念数据
- **THEN** 实际数据来源 MUST 为 DE 模块的 PostgreSQL（`concept` + `concept_stock` 表）
- **THEN** 返回的 DTO 类型 MUST 属于 `knowledge_center.domain.dtos` 包

#### Scenario: Domain 层无跨模块依赖

- **WHEN** 检查 `knowledge_center` 的 Domain 层代码
- **THEN** MUST NOT 存在对 `data_engineering` 模块类型的 import

### Requirement: IGraphRepository 扩展概念同步方法

`IGraphRepository` 接口 MUST 新增以下方法：

- `merge_concepts(concepts: list[ConceptGraphSyncDTO]) -> SyncResult`：批量写入/更新 Concept 节点及其与 Stock 的关系
- `delete_all_concept_relationships() -> int`：删除所有 BELONGS_TO_CONCEPT 关系，返回删除数量

#### Scenario: merge_concepts 写入概念数据

- **WHEN** 调用 `merge_concepts()` 传入概念数据列表
- **THEN** Neo4j 中 MUST 存在对应的 Concept 节点和 BELONGS_TO_CONCEPT 关系

#### Scenario: delete_all_concept_relationships 清理关系

- **WHEN** 调用 `delete_all_concept_relationships()`
- **THEN** Neo4j 中所有 `BELONGS_TO_CONCEPT` 关系 MUST 被删除
- **THEN** Concept 节点本身 MUST 保留（仅删关系）
- **THEN** 返回值为被删除的关系数量

### Requirement: 同步通过 REST API 触发

系统 SHALL 提供 REST 端点触发图谱同步：

```
POST /api/v1/knowledge-graph/sync
Body: { "mode": "full" | "incremental", "third_codes": ["..."], "target": "stock" | "concept" | "all" }
```

`third_codes` 仅在 `mode = "incremental"` 且 `target = "stock"` 时有效，为空时根据时间窗口自动确定范围。

`target` 为可选参数，默认值为 `"stock"`：

- `"stock"`：执行现有的股票元数据同步（行为不变）
- `"concept"`：执行概念数据全量同步（忽略 `mode` 和 `third_codes`，概念同步仅支持全量模式）
- `"all"`：依次执行股票同步和概念同步

#### Scenario: 通过 API 触发全量同步（默认行为不变）

- **WHEN** 发送 `POST /api/v1/knowledge-graph/sync` 且 body 为 `{"mode": "full"}`
- **THEN** 系统执行全量股票元数据同步并返回 200 及同步结果摘要（行为与变更前一致）

#### Scenario: 通过 API 触发概念同步

- **WHEN** 发送 `POST /api/v1/knowledge-graph/sync` 且 body 为 `{"mode": "full", "target": "concept"}`
- **THEN** 系统执行概念全量同步并返回 200 及概念同步结果摘要

#### Scenario: 通过 API 触发增量同步

- **WHEN** 发送 `POST /api/v1/knowledge-graph/sync` 且 body 为 `{"mode": "incremental", "third_codes": ["000001.SZ"]}`
- **THEN** 系统仅同步指定股票并返回 200 及同步结果摘要

#### Scenario: 通过 API 触发全部同步

- **WHEN** 发送 `POST /api/v1/knowledge-graph/sync` 且 body 为 `{"mode": "full", "target": "all"}`
- **THEN** 系统依次执行股票全量同步和概念全量同步，返回 200 及合并的同步结果摘要
