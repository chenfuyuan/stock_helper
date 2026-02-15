# Purpose

概念间关系的手动 CRUD 管理能力。PostgreSQL 为 Single Source of Truth，支持创建、查询、更新、删除概念关系，并通过 `ext_info`（JSONB）字段存储完整追溯上下文。

## ADDED Requirements

### Requirement: ConceptRelation 领域实体定义

系统 MUST 在 `knowledge_center/domain/model/concept_relation.py` 中定义 `ConceptRelation` 领域实体（Pydantic BaseModel）。

实体字段 MUST 包含：

- `id`（int | None）：主键，创建时为 None
- `source_concept_code`（str）：源概念板块代码
- `target_concept_code`（str）：目标概念板块代码
- `relation_type`（ConceptRelationType）：关系类型枚举
- `source_type`（RelationSourceType）：来源类型枚举（MANUAL / LLM）
- `status`（RelationStatus）：状态枚举（PENDING / CONFIRMED / REJECTED）
- `confidence`（float）：置信度，0.0~1.0
- `ext_info`（dict）：追溯上下文（JSONB 映射）
- `created_by`（str）：操作人标识
- `created_at`（datetime | None）
- `updated_at`（datetime | None）

#### Scenario: 实体定义在 Domain 层

- **WHEN** 检查 `ConceptRelation` 的定义位置
- **THEN** MUST 位于 `src/modules/knowledge_center/domain/model/concept_relation.py`
- **THEN** 实体 MUST 继承 Pydantic `BaseModel`

#### Scenario: 手动创建时置信度默认 1.0

- **WHEN** 创建一条 `source_type = MANUAL` 的关系且未指定 `confidence`
- **THEN** `confidence` MUST 默认为 1.0

### Requirement: ConceptRelationType 枚举定义

系统 MUST 在 `knowledge_center/domain/model/enums.py` 中新增 `ConceptRelationType` 枚举。

枚举值 MUST 包含：

- `IS_UPSTREAM_OF`：上游关系
- `IS_DOWNSTREAM_OF`：下游关系
- `COMPETES_WITH`：竞争关系
- `IS_PART_OF`：组成部分
- `ENABLER_FOR`：技术驱动

#### Scenario: 枚举值完整

- **WHEN** 检查 `ConceptRelationType` 枚举
- **THEN** MUST 包含上述 5 种关系类型

### Requirement: RelationSourceType 枚举定义

系统 MUST 在 `knowledge_center/domain/model/enums.py` 中新增 `RelationSourceType` 枚举。

枚举值 MUST 包含：

- `MANUAL`：手动创建
- `LLM`：LLM 推荐

#### Scenario: 枚举值完整

- **WHEN** 检查 `RelationSourceType` 枚举
- **THEN** MUST 包含 `MANUAL` 和 `LLM` 两种来源类型

### Requirement: RelationStatus 枚举定义

系统 MUST 在 `knowledge_center/domain/model/enums.py` 中新增 `RelationStatus` 枚举。

枚举值 MUST 包含：

- `PENDING`：待确认（LLM 推荐的默认状态）
- `CONFIRMED`：已确认
- `REJECTED`：已拒绝

#### Scenario: 枚举值完整

- **WHEN** 检查 `RelationStatus` 枚举
- **THEN** MUST 包含 `PENDING`、`CONFIRMED`、`REJECTED` 三种状态

### Requirement: IConceptRelationRepository Port 定义

系统 MUST 在 `knowledge_center/domain/ports/concept_relation_repository.py` 中定义 `IConceptRelationRepository` ABC 接口。

该接口 MUST 包含以下方法：

- `create(relation: ConceptRelation) -> ConceptRelation`：创建关系记录，返回含 id 的实体
- `get_by_id(relation_id: int) -> ConceptRelation | None`：按 ID 查询
- `list_relations(source_code: str | None, target_code: str | None, relation_type: ConceptRelationType | None, status: RelationStatus | None, source_type: RelationSourceType | None, limit: int, offset: int) -> list[ConceptRelation]`：列表查询，支持多维筛选
- `update(relation: ConceptRelation) -> ConceptRelation`：更新关系记录
- `delete(relation_id: int) -> bool`：删除关系记录，返回是否成功
- `batch_create(relations: list[ConceptRelation]) -> list[ConceptRelation]`：批量创建（供 LLM 推荐使用）
- `get_all_confirmed() -> list[ConceptRelation]`：查询所有已确认关系（供同步使用）
- `count(source_code: str | None, target_code: str | None, relation_type: ConceptRelationType | None, status: RelationStatus | None) -> int`：条件计数

方法 MUST 为异步方法（async）。

#### Scenario: Port 在 Domain 层定义

- **WHEN** 检查 `IConceptRelationRepository` 的定义位置
- **THEN** 该 ABC 接口 MUST 位于 `src/modules/knowledge_center/domain/ports/concept_relation_repository.py`
- **THEN** 接口方法的入参和出参 MUST 使用 Domain 层定义的类型

#### Scenario: create 返回含 ID 的实体

- **WHEN** 调用 `create()` 传入一条 `id = None` 的关系
- **THEN** 返回的 `ConceptRelation` MUST 包含数据库生成的 `id`

### Requirement: PostgreSQL 持久化实现

系统 MUST 在 `knowledge_center/infrastructure/persistence/` 下实现概念关系的 PostgreSQL 持久化。

包含：

- **ORM Model**：`ConceptRelationModel`（映射 `concept_relation` 表）
- **Repository 实现**：`PgConceptRelationRepository`，实现 `IConceptRelationRepository` 接口
- **Alembic Migration**：创建 `concept_relation` 表

`concept_relation` 表 MUST 包含：

- `id`（BIGINT PK, auto-increment）
- `source_concept_code`（VARCHAR, NOT NULL）
- `target_concept_code`（VARCHAR, NOT NULL）
- `relation_type`（VARCHAR, NOT NULL）
- `source_type`（VARCHAR, NOT NULL）
- `status`（VARCHAR, NOT NULL, DEFAULT 'PENDING'）
- `confidence`（FLOAT, NOT NULL, DEFAULT 1.0）
- `ext_info`（JSONB, NOT NULL, DEFAULT '{}'）
- `created_by`（VARCHAR, NOT NULL）
- `created_at`（TIMESTAMP WITH TZ, NOT NULL, DEFAULT NOW()）
- `updated_at`（TIMESTAMP WITH TZ, NOT NULL, DEFAULT NOW()）

约束：

- `UNIQUE (source_concept_code, target_concept_code, relation_type)`：同一对概念的同类型关系唯一
- `CHECK (confidence >= 0.0 AND confidence <= 1.0)`

#### Scenario: 数据库表创建

- **WHEN** 运行 Alembic migration
- **THEN** PostgreSQL 中 MUST 存在 `concept_relation` 表，包含上述所有字段和约束

#### Scenario: 唯一约束生效

- **WHEN** 尝试插入两条 `(source_concept_code='BK0001', target_concept_code='BK0002', relation_type='IS_UPSTREAM_OF')` 相同的记录
- **THEN** 第二次插入 MUST 触发唯一约束冲突

#### Scenario: ext_info 存储 JSONB 数据

- **WHEN** 创建关系时 `ext_info = {"note": "手动添加", "reason": "锂电池是新能源车的上游"}`
- **THEN** 数据库中 `ext_info` 字段 MUST 以 JSONB 格式存储该内容
- **THEN** 查询时 MUST 能还原为 Python dict

### Requirement: ext_info 内容校验

系统 MUST 在 Application 层对 `ext_info` 内容进行 Pydantic 校验，确保不同来源的追溯信息符合约定结构。

手动来源（`source_type = MANUAL`）的 `ext_info` MUST 符合 `ManualExtInfo` 结构：

- `note`（str, 可选）：操作备注
- `reason`（str, 可选）：建立关系的理由

LLM 来源（`source_type = LLM`）的 `ext_info` MUST 符合 `LLMExtInfo` 结构：

- `model`（str）：模型名称
- `model_version`（str, 可选）：模型版本
- `prompt`（str）：完整输入 prompt
- `raw_output`（str）：LLM 原始输出
- `parsed_result`（dict）：解析后的结构化结果
- `reasoning`（str）：推理依据
- `batch_id`（str, 可选）：批次 ID
- `analyzed_at`（str）：分析时间（ISO 格式）

#### Scenario: 手动来源 ext_info 校验通过

- **WHEN** 创建 `source_type = MANUAL` 的关系，`ext_info = {"note": "手动添加"}`
- **THEN** 校验 MUST 通过

#### Scenario: LLM 来源 ext_info 缺少必填字段

- **WHEN** 创建 `source_type = LLM` 的关系，`ext_info` 中缺少 `prompt` 字段
- **THEN** MUST 返回校验错误

### Requirement: REST API — 创建概念关系

系统 SHALL 提供 REST 端点：

```
POST /api/v1/knowledge-graph/concept-relations
```

请求体 MUST 包含：

- `source_concept_code`（str, 必填）
- `target_concept_code`（str, 必填）
- `relation_type`（str, 必填，枚举值）
- `confidence`（float, 可选，默认 1.0）
- `ext_info`（dict, 可选，默认 {}）
- `created_by`（str, 必填）

创建时 `source_type` MUST 自动设为 `MANUAL`，`status` MUST 自动设为 `CONFIRMED`。

#### Scenario: 成功创建返回 201

- **WHEN** 发送有效的创建请求
- **THEN** 返回 HTTP 201 及创建的关系记录（含 id）

#### Scenario: 源概念和目标概念相同返回 422

- **WHEN** `source_concept_code` 与 `target_concept_code` 相同
- **THEN** 返回 HTTP 422 及错误信息

#### Scenario: 无效关系类型返回 422

- **WHEN** `relation_type` 不在枚举范围内
- **THEN** 返回 HTTP 422 及错误信息

#### Scenario: 重复关系返回 409

- **WHEN** 创建的关系与已有记录的 (source, target, type) 重复
- **THEN** 返回 HTTP 409 及冲突信息

### Requirement: REST API — 查询概念关系列表

系统 SHALL 提供 REST 端点：

```
GET /api/v1/knowledge-graph/concept-relations
```

查询参数：

- `source_concept_code`（可选）：按源概念筛选
- `target_concept_code`（可选）：按目标概念筛选
- `relation_type`（可选）：按关系类型筛选
- `status`（可选）：按状态筛选
- `source_type`（可选）：按来源类型筛选
- `limit`（可选，默认 50）
- `offset`（可选，默认 0）

#### Scenario: 无筛选条件返回所有关系

- **WHEN** 发送 `GET /api/v1/knowledge-graph/concept-relations`（无查询参数）
- **THEN** 返回 HTTP 200 及关系列表（受 limit 限制）

#### Scenario: 按状态筛选

- **WHEN** 发送 `GET /api/v1/knowledge-graph/concept-relations?status=CONFIRMED`
- **THEN** 返回所有 `status = CONFIRMED` 的关系记录

#### Scenario: 按源概念筛选

- **WHEN** 发送 `GET /api/v1/knowledge-graph/concept-relations?source_concept_code=BK0493`
- **THEN** 返回所有 `source_concept_code = BK0493` 的关系记录

### Requirement: REST API — 查询单条概念关系

系统 SHALL 提供 REST 端点：

```
GET /api/v1/knowledge-graph/concept-relations/{id}
```

#### Scenario: 存在的关系返回 200

- **WHEN** 发送 `GET /api/v1/knowledge-graph/concept-relations/1` 且 id=1 的记录存在
- **THEN** 返回 HTTP 200 及关系详情（含完整 ext_info）

#### Scenario: 不存在的关系返回 404

- **WHEN** 发送 `GET /api/v1/knowledge-graph/concept-relations/99999` 且该 id 不存在
- **THEN** 返回 HTTP 404

### Requirement: REST API — 更新概念关系

系统 SHALL 提供 REST 端点：

```
PUT /api/v1/knowledge-graph/concept-relations/{id}
```

可更新字段：`relation_type`、`status`、`confidence`、`ext_info`。

`source_concept_code`、`target_concept_code`、`source_type` MUST NOT 可更新（需删除重建）。

#### Scenario: 确认 LLM 推荐的关系

- **WHEN** 发送 `PUT /api/v1/knowledge-graph/concept-relations/1` 且 body 为 `{"status": "CONFIRMED"}`
- **THEN** 返回 HTTP 200，该关系的 `status` MUST 更新为 `CONFIRMED`，`updated_at` MUST 更新

#### Scenario: 拒绝 LLM 推荐的关系

- **WHEN** 发送 `PUT /api/v1/knowledge-graph/concept-relations/1` 且 body 为 `{"status": "REJECTED"}`
- **THEN** 返回 HTTP 200，该关系的 `status` MUST 更新为 `REJECTED`

#### Scenario: 更新不存在的关系返回 404

- **WHEN** 发送 `PUT /api/v1/knowledge-graph/concept-relations/99999`
- **THEN** 返回 HTTP 404

### Requirement: REST API — 删除概念关系

系统 SHALL 提供 REST 端点：

```
DELETE /api/v1/knowledge-graph/concept-relations/{id}
```

#### Scenario: 成功删除返回 204

- **WHEN** 发送 `DELETE /api/v1/knowledge-graph/concept-relations/1` 且该记录存在
- **THEN** 返回 HTTP 204
- **THEN** 该记录 MUST 从 PostgreSQL 中删除

#### Scenario: 删除不存在的记录返回 404

- **WHEN** 发送 `DELETE /api/v1/knowledge-graph/concept-relations/99999`
- **THEN** 返回 HTTP 404

### Requirement: DI Container 注册

`KnowledgeCenterContainer` MUST 注册以下新增组件：

- `PgConceptRelationRepository` 作为 `IConceptRelationRepository` 的实现
- `ConceptRelationService` 应用服务（聚合 CRUD 操作）

#### Scenario: Repository 可注入

- **WHEN** 通过 DI 容器请求 `IConceptRelationRepository` 实例
- **THEN** MUST 返回 `PgConceptRelationRepository` 实例
