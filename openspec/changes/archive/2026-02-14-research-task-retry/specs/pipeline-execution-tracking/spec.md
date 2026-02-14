# Delta Spec: pipeline-execution-tracking

针对研究任务重试能力，对现有 pipeline-execution-tracking 规格的增量变更。

---

## MODIFIED Requirements

### Requirement: ResearchSession 生命周期管理

系统 SHALL 在每次研究流水线启动时创建一个 `ResearchSession` 记录，并在流水线结束后更新其最终状态。

`ResearchSession` 包含以下信息：唯一标识（UUID）、股票代码（symbol）、执行状态（running / completed / partial / failed）、选中的专家列表、执行选项、触发来源、创建时间、完成时间、总耗时（毫秒）、重试计数（`retry_count`，int，默认 0）、父会话标识（`parent_session_id`，UUID，可为 null）。

- 流水线启动时，状态 MUST 设为 `running`。
- 所有节点成功完成时，状态 MUST 更新为 `completed`。
- 部分节点成功、部分失败时，状态 MUST 更新为 `partial`。
- 所有节点均失败时，状态 MUST 更新为 `failed`。
- `completed_at` 和 `duration_ms` MUST 在流水线结束后写入。
- 首次执行时，`retry_count` MUST 为 `0`，`parent_session_id` MUST 为 `null`。
- 重试执行时，`retry_count` MUST 为源 session 的 `retry_count + 1`，`parent_session_id` MUST 指向被重试的源 session ID。

#### Scenario: 完整成功的研究流水线

- **WHEN** 用户发起一次研究请求，选择全部 5 个专家且不跳过辩论
- **THEN** 系统创建一个 `ResearchSession`（status=running，retry_count=0，parent_session_id=null），流水线全部节点执行成功后更新 status=completed，completed_at 和 duration_ms 均不为 null

#### Scenario: 部分专家失败

- **WHEN** 用户发起研究请求，其中 2 个专家执行失败、3 个成功，辩论和裁决正常完成
- **THEN** `ResearchSession` 最终 status=partial

#### Scenario: 全部失败

- **WHEN** 用户发起研究请求，所有专家均执行失败
- **THEN** `ResearchSession` 最终 status=failed，completed_at 和 duration_ms 仍被记录

#### Scenario: 重试时创建子 session

- **WHEN** 用户对 session A（retry_count=0）发起重试
- **THEN** 系统创建 session B，B.parent_session_id=A.id，B.retry_count=1，B.symbol 与 A 相同

#### Scenario: 多次重试 retry_count 递增

- **WHEN** 用户对 session B（retry_count=1）再次发起重试
- **THEN** 系统创建 session C，C.parent_session_id=B.id，C.retry_count=2

---

## ADDED Requirements

### Requirement: ResearchSession 数据库 schema 扩展

`research_sessions` 表 SHALL 通过 Alembic migration 新增以下列：

- `retry_count`（INTEGER，NOT NULL，DEFAULT 0）：重试计数
- `parent_session_id`（UUID，NULLABLE，FK → research_sessions.id）：父会话标识

ORM 模型 `ResearchSessionModel` SHALL 同步新增对应列定义。领域实体 `ResearchSession` SHALL 同步新增 `retry_count: int = 0` 和 `parent_session_id: UUID | None = None` 字段。

仓储映射函数（`_session_model_to_entity` / `_session_entity_to_model`）SHALL 包含新字段的转换。`update_session` 方法的 `.values()` 中无需包含 `retry_count` 和 `parent_session_id`（它们在创建时写入，不在更新时变更）。

#### Scenario: 新增列与现有数据兼容

- **WHEN** 对已有 research_sessions 数据运行 Alembic migration
- **THEN** 现有记录的 `retry_count` SHALL 为 `0`，`parent_session_id` SHALL 为 `null`

#### Scenario: ORM 模型包含新字段

- **WHEN** 检查 `ResearchSessionModel` 定义
- **THEN** SHALL 包含 `retry_count`（Integer, default 0）和 `parent_session_id`（UUID, nullable）列

#### Scenario: 领域实体包含新字段

- **WHEN** 检查 `ResearchSession` 定义
- **THEN** SHALL 包含 `retry_count: int = 0` 和 `parent_session_id: UUID | None = None` 字段
