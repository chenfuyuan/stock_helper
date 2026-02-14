# Spec: unified-llm-output-parser

## Purpose
提供供应商无关的统一泛型 LLM JSON 处理器，内聚全部预处理与 Pydantic 校验逻辑，消除各模块重复的解析实现，支持可选归一化钩子供 Agent 注入特有后处理。

## Requirements

### Requirement: 统一预处理管线

`parse_llm_json_output` 函数 SHALL 对 LLM 原始输出字符串按以下固定顺序执行预处理：

1. 空值检查：`raw` 为 `None`、空字符串或纯空白时，立即抛出 `LLMJsonParseError`。
2. 剥离 `<think>...</think>` 标签及其内容。
3. 剥离 Markdown 代码块（`` ```json `` 或 `` ``` `` 包裹的内容）。
4. 修复 JSON 字符串值内的未转义控制字符。
5. 执行 `json.loads` 解析。
6. 若步骤 5 失败，尝试从文本中提取首尾配对的 `{ }` 之间的内容（fallback），再次 `json.loads`。
7. 校验 JSON 根节点为 `dict` 类型。

#### Scenario: 纯净 JSON 直接解析
- **WHEN** LLM 返回 `{"score": 85, "signal": "bullish"}`
- **THEN** `parse_llm_json_output` 成功返回目标 DTO 实例

#### Scenario: Markdown 代码块包裹
- **WHEN** LLM 返回 `` ```json\n{"score": 85}\n``` ``
- **THEN** 预处理剥离代码块后成功解析

#### Scenario: think 标签 + Markdown 代码块
- **WHEN** LLM 返回 `<think>推理过程...</think>\n```json\n{"score": 85}\n```  `
- **THEN** 先剥离 think 标签，再剥离代码块，成功解析

#### Scenario: JSON 前后附带说明文字
- **WHEN** LLM 返回 `以下是分析结果：\n{"score": 85, "signal": "bullish"}\n以上为分析。`
- **THEN** fallback 提取 `{ }` 之间内容，成功解析

#### Scenario: 字符串值内含字面换行
- **WHEN** LLM 返回的 JSON 中某字符串字段包含未转义的字面换行符
- **THEN** 控制字符修复将其转为 `\\n`，`json.loads` 成功

#### Scenario: 完全非法内容
- **WHEN** LLM 返回纯文本且无 JSON 结构
- **THEN** 抛出 `LLMJsonParseError`

#### Scenario: 空返回
- **WHEN** LLM 返回空字符串或 `None`
- **THEN** 抛出 `LLMJsonParseError`

#### Scenario: JSON 根节点为数组
- **WHEN** LLM 返回 `[{"item": 1}]`（根节点为 list 而非 dict）
- **THEN** 抛出 `LLMJsonParseError`

### Requirement: 泛型 Pydantic 校验

`parse_llm_json_output` SHALL 接受泛型参数 `dto_type: type[T]`（其中 `T` 为 `pydantic.BaseModel` 子类），在预处理后调用 `dto_type.model_validate(data)` 完成反序列化与校验。校验失败时 SHALL 抛出 `LLMJsonParseError`。

#### Scenario: 字段校验成功
- **WHEN** LLM 返回的 JSON 字段完整且类型正确
- **THEN** 返回对应 Pydantic DTO 实例

#### Scenario: 必填字段缺失
- **WHEN** LLM 返回的 JSON 缺少 DTO 定义的必填字段
- **THEN** 抛出 `LLMJsonParseError`

#### Scenario: 字段类型错误
- **WHEN** LLM 返回的 JSON 中某字段类型与 DTO 定义不匹配
- **THEN** 抛出 `LLMJsonParseError`

### Requirement: 可选归一化钩子

`parse_llm_json_output` SHALL 接受可选参数 `normalizers: list[Callable[[dict], dict]]`。在 `json.loads` 成功后、Pydantic 校验前，按列表顺序依次执行每个钩子。

#### Scenario: 枚举值归一化
- **WHEN** Agent 注册钩子将中文枚举映射为英文枚举
- **THEN** 钩子执行后通过 Pydantic 校验

#### Scenario: 对象数组归一化为字符串列表
- **WHEN** Agent 注册钩子将对象数组转为字符串列表
- **THEN** 钩子执行后通过 Pydantic 校验

#### Scenario: 钩子执行异常
- **WHEN** 某个钩子函数抛出异常
- **THEN** 抛出 `LLMJsonParseError`，包含原始 dict 摘要

### Requirement: 通用异常类型 LLMJsonParseError

系统 SHALL 在 `src/shared/domain/exceptions.py` 中新增 `LLMJsonParseError`，继承 `AppException`。

#### Scenario: 统一处理器抛出 LLMJsonParseError
- **WHEN** `parse_llm_json_output` 在任一阶段失败
- **THEN** 抛出的异常类型为 `LLMJsonParseError`

#### Scenario: 模块 parser 转换异常类型
- **WHEN** 模块的 output_parser 薄包装捕获到 `LLMJsonParseError`
- **THEN** 转抛为模块领域异常，保留原始详情

### Requirement: 上下文标签用于日志

`parse_llm_json_output` SHALL 接受可选参数 `context_label: str`，在解析失败时将其写入日志。

#### Scenario: 带标签的失败日志
- **WHEN** 解析失败且传入了 `context_label`
- **THEN** WARNING 日志中包含该标签

### Requirement: 各 Agent output_parser 重构为薄包装

Agent 的 output_parser SHALL 重构为薄包装：调用 `parse_llm_json_output`，捕获 `LLMJsonParseError` 转为模块领域异常。

#### Scenario: 重构后公开函数签名不变
- **WHEN** 调用重构后的 parser 函数
- **THEN** 函数签名、参数、返回类型与重构前一致
