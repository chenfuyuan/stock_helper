# Purpose

data_engineering 模块新增 akshare 概念板块数据能力，包括外部数据获取、PostgreSQL 持久化和对外查询服务，为知识图谱的概念题材维度提供数据底座。

## ADDED Requirements

### Requirement: Concept 领域实体定义

系统 MUST 在 `data_engineering/domain/model/concept.py` 中定义概念相关领域实体。

`Concept` 实体字段 MUST 包含：

- `code`（str）：概念板块代码（如 `BK0493`），唯一标识
- `name`（str）：概念板块名称（如 "低空经济"）

`ConceptStock` 实体字段 MUST 包含：

- `concept_code`（str）：所属概念板块代码
- `third_code`（str）：股票代码，MUST 为系统标准格式（如 `000001.SZ`）
- `stock_name`（str）：股票名称

#### Scenario: 实体定义在 Domain 层

- **WHEN** 检查 `Concept` 和 `ConceptStock` 的定义位置
- **THEN** MUST 位于 `src/modules/data_engineering/domain/model/concept.py`
- **THEN** 实体 MUST 继承 Pydantic `BaseModel`

### Requirement: IConceptDataProvider Port 定义

系统 MUST 在 `data_engineering/domain/ports/providers/concept_data_provider.py` 中定义 `IConceptDataProvider` ABC 接口。

该接口 MUST 包含以下方法：

- `fetch_concept_list() -> list[ConceptInfoDTO]`：获取所有概念板块列表
- `fetch_concept_constituents(symbol: str) -> list[ConceptConstituentDTO]`：获取指定概念板块的成份股列表

方法 MUST 为异步方法（async）。

#### Scenario: Port 在 Domain 层定义

- **WHEN** 检查 `IConceptDataProvider` 的定义位置
- **THEN** 该 ABC 接口 MUST 位于 `src/modules/data_engineering/domain/ports/providers/concept_data_provider.py`
- **THEN** 接口方法的返回类型 MUST 使用 `data_engineering` 领域层定义的 DTO

### Requirement: ConceptInfoDTO 定义

系统 MUST 在 `data_engineering` 领域层定义 `ConceptInfoDTO`（Pydantic BaseModel），用于表示概念板块基本信息。

字段 MUST 包含：

- `code`（str）：概念板块代码（如 `BK0493`）
- `name`（str）：概念板块名称（如 "低空经济"）

#### Scenario: DTO 字段完整

- **WHEN** 从 akshare 获取概念列表并转换为 `ConceptInfoDTO`
- **THEN** 每条记录 MUST 包含非空的 `code` 和 `name`

#### Scenario: 空值过滤

- **WHEN** akshare 返回的某条记录 `code` 或 `name` 为空
- **THEN** 该记录 MUST 被过滤掉，不包含在返回结果中

### Requirement: ConceptConstituentDTO 定义

系统 MUST 在 `data_engineering` 领域层定义 `ConceptConstituentDTO`（Pydantic BaseModel），用于表示概念板块的成份股。

字段 MUST 包含：

- `stock_code`（str）：股票代码，MUST 为系统标准的 `third_code` 格式（如 `000001.SZ`）
- `stock_name`（str）：股票名称

#### Scenario: 深交所股票代码转换

- **WHEN** akshare 返回的原始股票代码为 `000001`（`0` 开头）
- **THEN** `ConceptConstituentDTO.stock_code` MUST 为 `000001.SZ`

#### Scenario: 上交所股票代码转换

- **WHEN** akshare 返回的原始股票代码以 `6` 开头（如 `601398`）
- **THEN** `stock_code` MUST 为 `601398.SH`

#### Scenario: 创业板股票代码转换

- **WHEN** akshare 返回的原始股票代码以 `3` 开头（如 `300750`）
- **THEN** `stock_code` MUST 为 `300750.SZ`

#### Scenario: 科创板股票代码转换

- **WHEN** akshare 返回的原始股票代码以 `68` 开头（如 `688001`）
- **THEN** `stock_code` MUST 为 `688001.SH`

#### Scenario: 北交所股票代码转换

- **WHEN** akshare 返回的原始股票代码以 `4` 或 `8` 开头（如 `430047`、`830799`）
- **THEN** `stock_code` MUST 为 `430047.BJ` 或 `830799.BJ`

### Requirement: AkShareConceptClient 实现

系统 MUST 在 `data_engineering/infrastructure/external_apis/akshare/` 下实现 `AkShareConceptClient`，实现 `IConceptDataProvider` 接口。

实现 MUST 满足以下约束：

- 调用 akshare 的 `stock_board_concept_name_em()` 获取概念列表
- 调用 akshare 的 `stock_board_concept_cons_em(symbol=<概念名称>)` 获取成份股
- akshare API 为同步调用，MUST 通过 `run_in_executor` 包装为异步方法
- 请求间 MUST 有可配置的间隔（默认 0.3s），避免触发限流
- 股票代码格式转换 MUST 在此 Adapter 内完成，对上层透明

#### Scenario: 获取概念列表

- **WHEN** 调用 `fetch_concept_list()`
- **THEN** 返回包含所有概念板块的 `list[ConceptInfoDTO]`
- **THEN** 列表 MUST 不为空（东方财富概念板块通常有 300+ 个）

#### Scenario: 获取概念成份股

- **WHEN** 调用 `fetch_concept_constituents(symbol="低空经济")`
- **THEN** 返回该概念下所有成份股的 `list[ConceptConstituentDTO]`
- **THEN** 每条记录的 `stock_code` MUST 为标准 `third_code` 格式

#### Scenario: API 调用失败时抛出领域异常

- **WHEN** akshare API 调用因网络错误或限流失败
- **THEN** MUST 抛出继承自 `AppException` 的领域异常
- **THEN** 异常信息 MUST 包含失败的 API 名称和原始错误描述

#### Scenario: 请求间隔控制

- **WHEN** 连续调用 `fetch_concept_constituents()` 多次
- **THEN** 每次调用之间 MUST 至少间隔配置的时间（默认 0.3s）

### Requirement: IConceptRepository Port 定义

系统 MUST 在 `data_engineering/domain/ports/repositories/concept_repo.py` 中定义 `IConceptRepository` ABC 接口。

该接口 MUST 包含以下方法：

- `upsert_concepts(concepts: list[Concept]) -> int`：批量 UPSERT 概念记录（by code），返回影响行数
- `replace_all_concept_stocks(mappings: list[ConceptStock]) -> int`：全量替换 `concept_stock` 表（先清后建），返回插入行数
- `get_all_concepts() -> list[Concept]`：查询所有概念记录
- `get_concept_stocks(concept_code: str) -> list[ConceptStock]`：查询指定概念的成份股
- `get_all_concepts_with_stocks() -> list[ConceptWithStocksDTO]`：查询所有概念及其成份股（聚合查询，供 KC 适配器使用）

方法 MUST 为异步方法（async）。

#### Scenario: Port 在 Domain 层定义

- **WHEN** 检查 `IConceptRepository` 的定义位置
- **THEN** 该 ABC 接口 MUST 位于 `src/modules/data_engineering/domain/ports/repositories/concept_repo.py`

#### Scenario: upsert_concepts 幂等写入

- **WHEN** 对同一 `code` 的概念执行两次 `upsert_concepts`
- **THEN** PostgreSQL 中仅存在一条该 `code` 的记录，`name` 和 `updated_at` 为最新值

#### Scenario: replace_all_concept_stocks 全量替换

- **WHEN** 调用 `replace_all_concept_stocks` 传入新的映射列表
- **THEN** `concept_stock` 表中的旧数据 MUST 被全部清除
- **THEN** 新数据 MUST 全部插入

### Requirement: ConceptWithStocksDTO 定义

系统 MUST 定义 `ConceptWithStocksDTO`（Pydantic BaseModel），用于聚合查询返回概念及其成份股。

字段 MUST 包含：

- `code`（str）：概念板块代码
- `name`（str）：概念板块名称
- `stocks`（list[ConceptStock]）：该概念下的成份股列表

#### Scenario: 聚合查询结果完整

- **WHEN** 调用 `get_all_concepts_with_stocks()` 且数据库中有概念数据
- **THEN** 每条 `ConceptWithStocksDTO` MUST 包含对应概念的所有成份股

### Requirement: PostgreSQL 持久化实现

系统 MUST 在 `data_engineering/infrastructure/persistence/` 下实现概念数据的 PostgreSQL 持久化。

包含：

- ORM Model：`ConceptModel`（映射 `concept` 表）和 `ConceptStockModel`（映射 `concept_stock` 表）
- Repository 实现：`PgConceptRepository`，实现 `IConceptRepository` 接口
- Alembic Migration：创建 `concept` 和 `concept_stock` 表

`concept` 表 MUST 包含：`id`（PK）、`code`（UNIQUE）、`name`、`created_at`、`updated_at`。

`concept_stock` 表 MUST 包含：`id`（PK）、`concept_code`、`third_code`、`stock_name`、`created_at`，并在 `(concept_code, third_code)` 上建立唯一约束。

#### Scenario: 数据库表创建

- **WHEN** 运行 Alembic migration
- **THEN** PostgreSQL 中 MUST 存在 `concept` 和 `concept_stock` 两张表

#### Scenario: 唯一约束生效

- **WHEN** 尝试插入重复的 `(concept_code, third_code)` 到 `concept_stock` 表
- **THEN** MUST 触发唯一约束冲突

### Requirement: SyncConceptDataCmd 同步命令

系统 MUST 在 `data_engineering/application/commands/` 下实现 `SyncConceptDataCmd`，负责从 akshare 获取概念数据并写入 PostgreSQL。

同步流程 MUST 包含：

1. 调用 `IConceptDataProvider.fetch_concept_list()` 获取所有概念
2. 对每个概念，调用 `fetch_concept_constituents(symbol)` 获取成份股（逐概念错误隔离）
3. 调用 `IConceptRepository.upsert_concepts()` 写入概念记录
4. 调用 `IConceptRepository.replace_all_concept_stocks()` 全量替换成份股映射

#### Scenario: 首次概念数据同步

- **WHEN** 触发概念数据同步且 PostgreSQL 中无概念数据
- **THEN** 从 akshare 获取所有概念及成份股并写入 PostgreSQL
- **THEN** `concept` 表记录数 MUST 等于成功获取的概念数
- **THEN** `concept_stock` 表记录数 MUST 等于所有概念成份股的总和

#### Scenario: 重复同步保持最新

- **WHEN** 再次触发概念数据同步
- **THEN** `concept` 表通过 UPSERT 更新（名称变更被捕获）
- **THEN** `concept_stock` 表全量替换为最新数据

#### Scenario: 部分概念获取失败不中断

- **WHEN** 获取某个概念的成份股时 akshare API 失败
- **THEN** 该概念的错误 MUST 被记录到日志（ERROR 级别）
- **THEN** 其余概念的同步 MUST 正常继续
- **THEN** 已成功获取的概念和成份股数据 MUST 被写入 PostgreSQL

#### Scenario: 同步完成后报告结果

- **WHEN** 同步命令执行完毕
- **THEN** MUST 返回结果摘要：概念总数、成功数、失败数、成份股总数、总耗时

### Requirement: DI Container 注册

`DataEngineeringContainer` MUST 注册以下实现并对外暴露：

- `AkShareConceptClient` 作为 `IConceptDataProvider` 的实现
- `PgConceptRepository` 作为 `IConceptRepository` 的实现
- `SyncConceptDataCmd` 应用命令
- 提供 `IConceptRepository` 实例供其他模块（KC）通过适配器访问

#### Scenario: 依赖注入可用

- **WHEN** 通过 DI 容器请求 `IConceptDataProvider` 实例
- **THEN** MUST 返回 `AkShareConceptClient` 实例

#### Scenario: Repository 可注入

- **WHEN** 通过 DI 容器请求 `IConceptRepository` 实例
- **THEN** MUST 返回 `PgConceptRepository` 实例
