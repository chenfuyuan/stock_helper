# Spec: unified-llm-output-parser

供应商无关的统一泛型 LLM JSON 处理器——提供 `parse_llm_json_output[T]` 纯解析函数，内聚全部预处理与 Pydantic 校验逻辑，替代 9 个模块各自重复的 output_parser 实现。支持可选归一化钩子供 Agent 注入特有后处理。

**测试约定**：每个 `#### Scenario:` 在变更交付时须对应至少一个自动化测试用例（单元或集成）；实现顺序可先实现再补测，以完整测试通过为需求完成标准。

---

## ADDED Requirements

### Requirement: 统一预处理管线

`parse_llm_json_output` 函数 SHALL 对 LLM 原始输出字符串按以下固定顺序执行预处理：

1. 空值检查：`raw` 为 `None`、空字符串或纯空白时，立即抛出 `LLMJsonParseError`。
2. 剥离 `<think>...</think>` 标签及其内容（reasoning model 的思考过程）。
3. 剥离 Markdown 代码块（`` ```json `` 或 `` ``` `` 包裹的内容），自动去除语言标识。
4. 修复 JSON 字符串值内的未转义控制字符（字面换行 `\n`、回车 `\r`、制表 `\t` 等）。
5. 执行 `json.loads` 解析。
6. 若步骤 5 失败，尝试从文本中提取首尾配对的 `{ }` 之间的内容（fallback），再次 `json.loads`。
7. 校验 JSON 根节点为 `dict` 类型。

管线中任一步骤无法挽救时 SHALL 抛出 `LLMJsonParseError`，携带错误详情（阶段、原始文本长度、具体错误消息）。

#### Scenario: 纯净 JSON 直接解析

- **WHEN** LLM 返回 `{"score": 85, "signal": "bullish"}`（无任何包裹）
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

- **WHEN** LLM 返回的 JSON 中某字符串字段包含未转义的字面换行符（`\n`）
- **THEN** 控制字符修复将其转为 `\\n`，`json.loads` 成功

#### Scenario: 完全非法内容

- **WHEN** LLM 返回纯文本 `我无法完成这个任务`（无任何 JSON 结构）
- **THEN** 抛出 `LLMJsonParseError`，`details` 中包含 `json_error` 信息

#### Scenario: 空返回

- **WHEN** LLM 返回空字符串或 `None`
- **THEN** 抛出 `LLMJsonParseError`，`message` 说明内容为空

#### Scenario: JSON 根节点为数组

- **WHEN** LLM 返回 `[{"item": 1}]`（根节点为 list 而非 dict）
- **THEN** 抛出 `LLMJsonParseError`，`message` 说明根节点须为对象

---

### Requirement: 泛型 Pydantic 校验

`parse_llm_json_output` SHALL 接受泛型参数 `dto_type: type[T]`（其中 `T` 为 `pydantic.BaseModel` 子类），在预处理后调用 `dto_type.model_validate(data)` 完成反序列化与校验。校验失败时 SHALL 抛出 `LLMJsonParseError`，`details` 中包含 Pydantic 校验错误摘要。

#### Scenario: 字段校验成功

- **WHEN** LLM 返回的 JSON 字段完整且类型正确
- **THEN** 返回对应 Pydantic DTO 实例，所有字段值正确

#### Scenario: 必填字段缺失

- **WHEN** LLM 返回的 JSON 缺少 DTO 定义的必填字段
- **THEN** 抛出 `LLMJsonParseError`，`details.validation_errors` 包含缺失字段的位置与错误信息

#### Scenario: 字段类型错误

- **WHEN** LLM 返回的 JSON 中某字段类型与 DTO 定义不匹配（如 string 应为 int）
- **THEN** 抛出 `LLMJsonParseError`，`details.validation_errors` 包含类型不匹配的详情

---

### Requirement: 可选归一化钩子

`parse_llm_json_output` SHALL 接受可选参数 `normalizers: list[Callable[[dict], dict]]`。在 `json.loads` 成功后、Pydantic 校验前，按列表顺序依次执行每个钩子，将 `dict` 传入并以返回值替换。

钩子执行异常时 SHALL 抛出 `LLMJsonParseError`（包含原始 dict 和钩子异常信息），不吞没异常。

#### Scenario: 枚举值归一化

- **WHEN** Agent 注册钩子将 `"Undervalued (低估)"` 映射为 `"Undervalued"`，且 LLM 返回的 JSON 中 `valuation_verdict` 为 `"Undervalued (低估)"`
- **THEN** 钩子执行后 dict 中 `valuation_verdict` 变为 `"Undervalued"`，Pydantic 校验通过

#### Scenario: 对象数组归一化为字符串列表

- **WHEN** Agent 注册钩子将 `supporting_arguments` 从 `[{"dimension": "...", "argument": "..."}]` 转为 `["...: ..."]`
- **THEN** 钩子执行后 `supporting_arguments` 为 `list[str]`，Pydantic 校验通过

#### Scenario: 无钩子时直接校验

- **WHEN** 调用方未传 `normalizers` 参数或传空列表
- **THEN** 跳过归一化步骤，直接进入 Pydantic 校验

#### Scenario: 钩子执行异常

- **WHEN** 某个钩子函数抛出异常（如 KeyError）
- **THEN** 抛出 `LLMJsonParseError`，`details` 中包含钩子异常信息和原始 dict 摘要

---

### Requirement: 通用异常类型 LLMJsonParseError

系统 SHALL 在 `src/shared/domain/exceptions.py` 中新增 `LLMJsonParseError`，继承 `AppException`。该异常用于统一处理器抛出的所有解析失败场景。

各 Bounded Context 的 output_parser 薄包装 SHALL 捕获 `LLMJsonParseError` 并转为模块自己的 `LLMOutputParseError`，保持领域异常独立性。

#### Scenario: 统一处理器抛出 LLMJsonParseError

- **WHEN** `parse_llm_json_output` 在任一阶段失败
- **THEN** 抛出的异常类型为 `LLMJsonParseError`（而非各模块的 `LLMOutputParseError`），包含 `message`、`details`（含 `raw_length`、`json_error` 或 `validation_errors`）

#### Scenario: 模块 parser 转换异常类型

- **WHEN** Research 模块的 output_parser 薄包装调用 `parse_llm_json_output` 捕获到 `LLMJsonParseError`
- **THEN** 转抛为 `src.modules.research.domain.exceptions.LLMOutputParseError`，保留原始 `message` 和 `details`

---

### Requirement: 上下文标签用于日志

`parse_llm_json_output` SHALL 接受可选参数 `context_label: str`（如 `"宏观情报员"`、`"裁决"`），在解析失败时将其写入日志，便于定位是哪个 Agent 的 LLM 输出出了问题。

#### Scenario: 带标签的失败日志

- **WHEN** `parse_llm_json_output` 以 `context_label="财务审计员"` 调用且解析失败
- **THEN** WARNING 级别日志中包含 `"财务审计员"` 标识和 LLM 原始输出摘要（截断至合理长度）

#### Scenario: 无标签时使用默认

- **WHEN** 调用方未传 `context_label`
- **THEN** 日志中使用空字符串或通用标识，不报错

---

### Requirement: 各 Agent output_parser 重构为薄包装

Research（5 个）、Debate（3 个）、Judge（1 个）共 9 个 Agent 的 output_parser SHALL 重构为薄包装：调用 `parse_llm_json_output`，传入目标 DTO 类型和可选归一化钩子，捕获 `LLMJsonParseError` 转为模块领域异常。

重构后的 parser 公开函数签名 SHALL 保持不变（如 `parse_macro_intelligence_result(raw: str) -> MacroIntelligenceResultDTO`），确保调用方（Agent Adapter）无需修改。

#### Scenario: 无特有归一化的 Agent（如 macro_intelligence）

- **WHEN** `parse_macro_intelligence_result("```json\n{...}\n```")` 被调用
- **THEN** 内部委托 `parse_llm_json_output(raw, MacroIntelligenceResultDTO, context_label="宏观情报员")`，行为与重构前一致

#### Scenario: 有特有归一化的 Agent（如 valuation_modeler）

- **WHEN** `parse_valuation_result(raw)` 被调用，且 LLM 返回中 `valuation_verdict` 为 `"Fair (合理)"`
- **THEN** 内部委托 `parse_llm_json_output(raw, ValuationResultDTO, normalizers=[normalize_verdict], context_label="估值建模师")`，verdict 归一化为 `"Fair"` 后通过校验

#### Scenario: 重构后公开函数签名不变

- **WHEN** Agent Adapter 调用 `parse_technical_analysis_result(raw)`
- **THEN** 函数签名、参数、返回类型与重构前完全一致，Adapter 代码无需修改
