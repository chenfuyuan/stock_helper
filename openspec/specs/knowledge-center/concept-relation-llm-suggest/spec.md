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
- **THEN** 关系类型 MUST 为 `IS_UPSTREAM_OF` 或 `IS_DOWNSTREAM_OF`
- **THEN** confidence MUST 在 0.0~1.0 范围内
- **THEN** reasoning MUST 包含合理的产业逻辑说明

#### Scenario: LLM 输出格式异常处理

- **WHEN** LLM 返回的 JSON 格式不完整或解析失败
- **THEN** MUST 返回空列表而不是抛出异常
- **THEN** MUST 记录警告日志，包含原始 LLM 输出片段

#### Scenario: 重复关系去重

- **WHEN** LLM 推荐了多条 (source, target, type) 相同的关系
- **THEN** MUST 去重，每条唯一关系只保留一个
- **THEN** 保留置信度更高的版本（如果置信度不同）

### Requirement: SuggestConceptRelationsCmd 应用命令

系统 MUST 在 `knowledge_center/application/commands/suggest_concept_relations_command.py` 中实现 `SuggestConceptRelationsCmd`，编排 LLM 推荐流程。

该命令 MUST 实现以下流程：

1. **构建概念列表**：将输入的 `(code, name)` 转换为 `ConceptForAnalysis` DTO
2. **调用分析器**：调用 `IConceptRelationAnalyzer.analyze_relations()`
3. **过滤低置信度**：按 `min_confidence` 参数过滤结果
4. **构建 ext_info**：为每条关系构建 `LLMExtInfo`，记录完整追溯信息
5. **批量写入**：调用 `IConceptRelationRepository.batch_create()` 跳过重复关系
6. **返回统计**：返回推荐数量、创建数量、跳过数量

#### Scenario: 成功推荐返回统计

- **WHEN** 输入 5 个概念，LLM 推荐 8 条关系，置信度阈值 0.6，其中 6 条满足阈值
- **THEN** 返回 `total_suggested=8, created_count=6, skipped_count=2`
- **THEN** 创建的 6 条关系 `source_type=LLM, status=PENDING`
- **THEN** 每条关系的 `ext_info` MUST 包含 `LLMExtInfo` 结构

#### Scenario: 置信度过滤

- **WHEN** 设置 `min_confidence=0.8`，LLM 推荐的关系中有 3 条低于 0.8
- **THEN** 这 3 条低置信度关系 MUST 被过滤掉
- **THEN** 只处理置信度 >= 0.8 的关系

#### Scenario: 批量写入跳过重复

- **WHEN** 批量写入时遇到唯一约束冲突
- **THEN** Repository MUST 跳过重复记录，不抛出异常
- **THEN** 被跳过的记录 MUST 计入 `skipped_count` 统计

### Requirement: REST API — LLM 推荐概念关系

系统 SHALL 提供 REST 端点：

```
POST /api/v1/knowledge-graph/concept-relations/llm-suggest
```

请求体 MUST 包含：

- `concept_codes_with_names`（list[tuple[str, str]]，必填）：概念列表 [(code, name), ...]
- `min_confidence`（float，可选，默认 0.6）：最低置信度阈值
- `created_by`（str，必填）：操作人标识

#### Scenario: 成功推荐返回 200

- **WHEN** 发送有效的推荐请求，LLM 成功分析
- **THEN** 返回 HTTP 200 及推荐结果统计
- **THEN** 推荐的关系 MUST 已写入 PostgreSQL

#### Scenario: 概念数量不足返回 400

- **WHEN** `concept_codes_with_names` 包含少于 2 个概念
- **THEN** 返回 HTTP 400 及错误信息

#### Scenario: LLM 服务异常返回 500

- **WHEN** `llm_platform` 服务不可用或返回错误
- **THEN** 返回 HTTP 500 及错误信息
- **THEN** 不得写入任何关系到数据库

### Requirement: DI Container 注册

`KnowledgeCenterContainer` MUST 注册以下新增组件：

- `LLMConceptRelationAnalyzer` 作为 `IConceptRelationAnalyzer` 的实现
- `SuggestConceptRelationsCmd` 应用命令
- 从 `LLMPlatformContainer` 注入 `LLMService` 供分析器使用

#### Scenario: Analyzer 可注入

- **WHEN** 通过 DI 容器请求 `IConceptRelationAnalyzer` 实例
- **THEN** MUST 返回 `LLMConceptRelationAnalyzer` 实例
- **THEN** 该实例 MUST 已注入 `LLMService` 依赖

#### Scenario: 命令可注入

- **WHEN** 通过 DI 容器请求 `SuggestConceptRelationsCmd` 实例
- **THEN** MUST 返回已注入所有依赖的命令实例
