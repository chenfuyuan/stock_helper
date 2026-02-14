## 1. data_engineering — 领域层（实体 + DTO + Port）

- [x] 1.1 创建 `Concept` 和 `ConceptStock` 领域实体，放在 `data_engineering/domain/model/concept.py`
- [x] 1.2 创建 `ConceptInfoDTO`、`ConceptConstituentDTO`、`ConceptWithStocksDTO`，放在 `data_engineering/domain/dtos/concept_dtos.py`
- [x] 1.3 创建 `IConceptDataProvider` ABC 接口，放在 `data_engineering/domain/ports/providers/concept_data_provider.py`，定义 `fetch_concept_list()` 和 `fetch_concept_constituents(symbol)` 两个 async 方法
- [x] 1.4 创建 `IConceptRepository` ABC 接口，放在 `data_engineering/domain/ports/repositories/concept_repo.py`，定义 `upsert_concepts()`、`replace_all_concept_stocks()`、`get_all_concepts()`、`get_concept_stocks()`、`get_all_concepts_with_stocks()` 方法

## 2. data_engineering — 基础设施层（akshare 适配器）

- [x] 2.1 创建 `infrastructure/external_apis/akshare/` 目录结构（`__init__.py`、`client.py`、`converters/` 子目录）
- [x] 2.2 实现股票代码格式转换工具（akshare 原始代码 → `third_code` 格式），放在 `converters/stock_code_converter.py`。覆盖规则：`6`/`68` 开头 → `.SH`，`0`/`3` 开头 → `.SZ`，`4`/`8` 开头 → `.BJ`
- [x] 2.3 实现 `AkShareConceptClient`（`client.py`），实现 `IConceptDataProvider` 接口。调用 `stock_board_concept_name_em()` 和 `stock_board_concept_cons_em(symbol)`，使用 `run_in_executor` 异步包装，加入可配置请求间隔（默认 0.3s）

## 3. data_engineering — 基础设施层（PostgreSQL 持久化）

- [x] 3.1 创建 ORM Model：`ConceptModel`（映射 `concept` 表）和 `ConceptStockModel`（映射 `concept_stock` 表），放在 `infrastructure/persistence/models/concept_model.py`
- [x] 3.2 创建 Alembic migration：建 `concept` 表（id, code UNIQUE, name, created_at, updated_at）和 `concept_stock` 表（id, concept_code, third_code, stock_name, created_at, UNIQUE(concept_code, third_code)）
- [x] 3.3 实现 `PgConceptRepository`，放在 `infrastructure/persistence/repositories/pg_concept_repo.py`，实现 `IConceptRepository` 全部方法（upsert_concepts 使用 ON CONFLICT DO UPDATE，replace_all_concept_stocks 先 DELETE 再 INSERT）

## 4. data_engineering — 应用层（同步命令）

- [x] 4.1 实现 `SyncConceptDataCmd`，放在 `application/commands/sync_concept_data_cmd.py`：获取概念列表 → 逐概念获取成份股（错误隔离）→ upsert 概念 → 全量替换成份股映射 → 报告结果
- [x] 4.2 在 `DataEngineeringContainer` 中注册 `AkShareConceptClient`（IConceptDataProvider）、`PgConceptRepository`（IConceptRepository）、`SyncConceptDataCmd`，并对外暴露 `IConceptRepository` 实例供 KC 模块使用

## 5. knowledge_center — 领域层扩展

- [x] 5.1 在 `domain/model/enums.py` 中新增 `NodeLabel.CONCEPT` 和 `RelationshipType.BELONGS_TO_CONCEPT` 枚举值
- [x] 5.2 在 `domain/model/` 下创建 `concept_node.py`，定义 `ConceptNode` 实体（`code: str`, `name: str`）
- [x] 5.3 在 `domain/dtos/` 下创建 `concept_sync_dtos.py`，定义 `ConceptGraphSyncDTO`（概念同步用 DTO，含 `code`、`name`、`stock_third_codes: list[str]`）
- [x] 5.4 扩展 `domain/ports/graph_repository.py` 中的 `IGraphRepository`，新增 `merge_concepts()` 和 `delete_all_concept_relationships()` 方法签名

## 6. knowledge_center — 基础设施层扩展

- [x] 6.1 在 `infrastructure/adapters/` 下创建概念数据适配器（如 `concept_data_adapter.py`），注入 DE 的 `IConceptRepository`，调用 `get_all_concepts_with_stocks()` 从 PostgreSQL 读取数据，转换为 KC 的 `ConceptGraphSyncDTO`
- [x] 6.2 扩展 `infrastructure/persistence/neo4j_graph_repository.py`，实现 `merge_concepts()`：Cypher UNWIND + MERGE Concept 节点 + MATCH Stock + MERGE 关系
- [x] 6.3 扩展 `neo4j_graph_repository.py`，实现 `delete_all_concept_relationships()`：删除所有 BELONGS_TO_CONCEPT 关系并返回数量
- [x] 6.4 扩展 `ensure_constraints()` 方法，新增 `Concept.code` 唯一约束创建
- [x] 6.5 扩展 `find_neighbors()` 实现，当 `dimension="concept"` 时使用 `dimension_name` 参数匹配 Concept 节点查询邻居
- [x] 6.6 扩展 `find_stock_graph()` 实现，确保返回结果包含 Concept 节点和 BELONGS_TO_CONCEPT 关系

## 7. knowledge_center — 应用层扩展

- [x] 7.1 创建 `application/commands/sync_concept_graph_command.py`，实现概念图谱同步命令：从 DE PG 读取概念数据 → 先删后建 Neo4j 关系 → 报告结果
- [x] 7.2 扩展 `application/services/graph_service.py` 的 `GraphService`，新增 `sync_concept_graph()` 方法
- [x] 7.3 扩展 `GraphService` 的 `get_stock_neighbors()` 方法，支持 `dimension_name` 可选参数传递

## 8. knowledge_center — 表现层扩展

- [x] 8.1 扩展同步 API 的请求 DTO（`application/dtos/graph_api_dtos.py`），新增 `target` 字段（枚举：`stock`/`concept`/`all`，默认 `stock`）
- [x] 8.2 扩展 `presentation/rest/graph_router.py` 的同步端点，根据 `target` 参数分发到对应同步命令
- [x] 8.3 扩展邻居查询端点，新增 `dimension_name` 可选查询参数，`dimension` 枚举值增加 `concept`

## 9. DI 容器与集成

- [x] 9.1 更新 `KnowledgeCenterContainer`，注入概念数据适配器和新的同步命令到 DI 链路
- [x] 9.2 添加 `akshare` 到项目依赖（`requirements.txt` 或 `pyproject.toml`）
- [x] 9.3 端到端手动验证：触发 DE 概念同步（akshare → PG）→ 触发 KC 概念同步（PG → Neo4j）→ 验证 Neo4j 中 Concept 节点和关系

## 10. 自动化测试

- [x] 10.1 单元测试：股票代码格式转换工具（覆盖深交所/上交所/创业板/科创板/北交所各场景）
- [x] 10.2 单元测试：`AkShareConceptClient`（mock akshare API，验证 DTO 转换和异常处理）
- [x] 10.3 单元测试：`SyncConceptDataCmd`（mock Provider + Repository，验证同步流程和错误隔离）
- [x] 10.4 单元测试：KC 概念数据适配器（mock IConceptRepository，验证 DTO 转换）
- [x] 10.5 单元测试：`SyncConceptGraphCommand`（mock GraphRepository + Adapter，验证先删后建流程）
- [x] 10.6 集成测试：`PgConceptRepository` 的 CRUD（使用测试 PostgreSQL，验证 upsert_concepts、replace_all_concept_stocks、get_all_concepts_with_stocks）
- [x] 10.7 集成测试：Neo4j Concept 节点和关系的 CRUD（使用测试 Neo4j 实例，验证 merge_concepts、delete_all_concept_relationships、ensure_constraints）
- [x] 10.8 集成测试：概念维度邻居查询和关系网络查询
