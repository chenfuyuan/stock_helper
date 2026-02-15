# Purpose

基于 LLM 的概念关系自动推荐能力。给定一组概念，调用 `llm_platform` 分析并输出推荐的关系列表，结果写入 PostgreSQL 待人工确认，`ext_info` 中完整记录 LLM 的输入输出和推理过程。

## ADDED Requirements

### Requirement: IConceptRelationAnalyzer Port 定义

系统 MUST 在 `knowledge_center/domain/ports/concept_relation_analyzer.py` 中定义 `IConceptRelationAnalyzer` ABC 接口。

该接口 MUST 包含以下方法：

- `analyze_relations(concepts: list[ConceptForAnalysis]) -> list[SuggestedRelation]`：分析给定概念集合之间的关系，返回推荐的关系列表

方法 MUST 为异步方法（async）。

`ConceptForAnalysis` DTO MUST 包含：`code`（str）、`name`（str）。

`SuggestedRelation` DTO MUST 包含：

- `source_concept_code`（str）
- `source_concept_name`（str）
- `target_concept_code`（str）
- `target_concept_name`（str）
- `relation_type`（ConceptRelationType）
- `confidence`（float，0.0~1.0）
- `reasoning`（str）：推理依据

#### Scenario: Port 在 Domain 层定义

- **WHEN** 检查 `IConceptRelationAnalyzer` 的定义位置
- **THEN** 该 ABC 接口 MUST 位于 `src/modules/knowledge_center/domain/ports/concept_relation_analyzer.py`
- **THEN** 接口方法使用的 DTO MUST 定义在 `knowledge_center/domain/dtos/` 中

### Requirement: LLMConceptRelationAnalyzer Adapter 实现

系统 MUST 在 `knowledge_center/infrastructure/adapters/llm_concept_relation_analyzer.py` 中实现 `LLMConceptRelationAnalyzer`，实现 `IConceptRelationAnalyzer` 接口。

实现 MUST 满足以下约束：

- 通过构造函数注入 `llm_platform` 的 `LLMService`
- 构建分析用 prompt，包含所有输入概念的名称和代码
- 调用 `LLMService.generate()` 获取 LLM 分析结果
- 解析 LLM 输出为结构化的 `SuggestedRelation` 列表
- 返回结果中包含每条推荐关系的 confidence 和 reasoning

#### Scenario: 分析两个有上下游关系的概念

- **WHEN** 输入概念列表包含"锂电池"（BK0001）和"新能源车"（BK0002）
- **THEN** 返回的推荐关系列表 MUST 包含至少一条关系
- **THEN** 每条推荐关系 MUST 包含 `relation_type`、`confidence`、`reasoning`

#### Scenario: LLM 调用失败时抛出领域异常

- **WHEN** `LLMService.generate()` 调用失败（网络错误或模型不可用）
- **THEN** MUST 抛出继承自 `AppException` 的领域异常
- **THEN** 异常信息 MUST 包含失败原因

#### Scenario: LLM 输出格式异常时降级处理

- **WHEN** LLM 返回的内容无法解析为预期的结构化格式
- **THEN** MUST 记录 WARNING 日志，包含原始输出内容
- **THEN** 返回空列表，不抛出异常

### Requirement: Prompt 工程

`LLMConceptRelationAnalyzer` 的 prompt MUST 满足以下约定：

- system_message MUST 设定 LLM 作为"产业链分析专家"的角色
- prompt MUST 包含所有输入概念的 code 和 name
- prompt MUST 明确要求 LLM 以 JSON 格式输出，包含：源概念、目标概念、关系类型、置信度、推理依据
- prompt MUST 约束关系类型在 `ConceptRelationType` 枚举范围内
- prompt MUST 要求置信度为 0.0~1.0 的浮点数

#### Scenario: Prompt 包含所有输入概念

- **WHEN** 输入 3 个概念（"锂电池"、"新能源车"、"充电桩"）
- **THEN** 构建的 prompt MUST 包含这 3 个概念的 code 和 name

#### Scenario: Prompt 约束输出格式

- **WHEN** 构建 prompt
- **THEN** prompt 中 MUST 包含 JSON 输出格式示例和关系类型枚举列表

### Requirement: LLM 推荐命令（SuggestConceptRelationsCmd）

系统 MUST 在 `knowledge_center/application/commands/suggest_concept_relations_command.py` 中实现 `SuggestConceptRelationsCmd`。

该命令编排以下流程：

1. 接收输入的概念代码列表
2. 从 PostgreSQL（通过 `data_engineering` 适配器或本模块已有数据）查询概念名称
3. 调用 `IConceptRelationAnalyzer.analyze_relations()` 获取推荐结果
4. 为每条推荐关系构建 `ConceptRelation` 实体，`source_type = LLM`，`status = PENDING`
5. 构建 `ext_info`（LLMExtInfo），包含完整的 LLM 输入 prompt、原始输出、解析结果、推理依据、模型版本、分析时间
6. 调用 `IConceptRelationRepository.batch_create()` 批量写入 PostgreSQL
7. 过滤已存在的重复关系（跳过而非报错）

#### Scenario: 成功推荐并写入 PostgreSQL

- **WHEN** 输入概念列表 ["BK0001", "BK0002", "BK0003"]
- **THEN** 系统调用 LLM 分析并将推荐结果写入 `concept_relation` 表
- **THEN** 写入的记录 `source_type` MUST 为 `LLM`
- **THEN** 写入的记录 `status` MUST 为 `PENDING`
- **THEN** 写入的记录 `ext_info` MUST 包含 `prompt`、`raw_output`、`reasoning`、`model`、`analyzed_at` 字段

#### Scenario: 推荐的关系已存在时跳过

- **WHEN** LLM 推荐的某条关系 (source, target, type) 在 PostgreSQL 中已存在
- **THEN** 该条关系 MUST 被跳过，不写入，不报错
- **THEN** 跳过的记录数 MUST 在返回结果中体现

#### Scenario: 推荐完成后报告结果

- **WHEN** 推荐命令执行完毕
- **THEN** MUST 返回结果摘要：推荐总数、写入数、跳过数（已存在）、失败数

### Requirement: REST API — LLM 推荐概念关系

系统 SHALL 提供 REST 端点：

```
POST /api/v1/knowledge-graph/concept-relations/llm-suggest
```

请求体 MUST 包含：

- `concept_codes`（list[str], 必填）：待分析的概念代码列表，至少 2 个
- `created_by`（str, 必填）：操作人标识

#### Scenario: 成功推荐返回 200

- **WHEN** 发送有效的推荐请求，包含 3 个概念代码
- **THEN** 返回 HTTP 200 及推荐结果摘要（推荐总数、写入数、跳过数）

#### Scenario: 概念代码不足 2 个返回 422

- **WHEN** 发送的 `concept_codes` 只有 1 个
- **THEN** 返回 HTTP 422 及错误信息

#### Scenario: 概念代码不存在返回 422

- **WHEN** 发送的 `concept_codes` 中包含不存在的概念代码
- **THEN** 返回 HTTP 422 及错误信息，指出不存在的概念代码

### Requirement: DI Container 注册

`KnowledgeCenterContainer` MUST 注册以下新增组件：

- `LLMConceptRelationAnalyzer` 作为 `IConceptRelationAnalyzer` 的实现（注入 `LLMService`）
- `SuggestConceptRelationsCmd` 应用命令

#### Scenario: Analyzer 可注入

- **WHEN** 通过 DI 容器请求 `IConceptRelationAnalyzer` 实例
- **THEN** MUST 返回 `LLMConceptRelationAnalyzer` 实例
- **THEN** 该实例 MUST 已注入 `LLMService`
