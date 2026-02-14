# Spec: llm-json-retry

## Purpose
提供带错误反馈的 LLM JSON 重试能力，确保 LLM 输出在解析失败或校验失败时能够根据错误摘要进行自我修正。

## Requirements

### Requirement: generate_and_parse 封装调用与解析

`generate_and_parse` 异步函数 SHALL 接受以下参数：

- `llm_call: Callable[..., Awaitable[str]]` — LLM 回调函数
- `dto_type: type[T]` — 目标 Pydantic DTO 类型
- `prompt: str` — 原始 prompt
- `system_message: str | None` — 可选 system message
- `temperature: float` — 采样温度，默认 0.7
- `normalizers: list[Callable[[dict], dict]] | None` — 可选归一化钩子
- `max_retries: int` — 最大重试次数，默认 1
- `context_label: str` — 上下文标签，用于日志

函数 SHALL 调用 `llm_call` 获取 LLM 原始输出，然后委托 `parse_llm_json_output` 解析。首次解析成功时直接返回 DTO 实例。

#### Scenario: 首次调用即成功
- **WHEN** `generate_and_parse` 被调用，LLM 首次返回合法 JSON 且通过 Pydantic 校验
- **THEN** 仅调用 `llm_call` 一次，返回目标 DTO 实例

#### Scenario: 参数透传到 llm_call
- **WHEN** `generate_and_parse` 以 `prompt="分析..."`, `system_message="你是..."`, `temperature=0.3` 调用
- **THEN** `llm_call` 被调用时接收到相同的 `prompt`、`system_message`、`temperature` 参数

### Requirement: 解析失败时带错误反馈重试

当 `parse_llm_json_output` 抛出 `LLMJsonParseError` 且剩余重试次数 > 0 时，`generate_and_parse` SHALL 构造包含错误摘要的修正 prompt 再次调用 `llm_call`。

修正 prompt SHALL 包含：原始 prompt + 错误反馈指令（含具体错误信息），指示 LLM 仅输出 JSON 对象，不包含额外文字或 Markdown 标记。

#### Scenario: 首次失败、重试成功
- **WHEN** LLM 首次返回非法 JSON（如包含 Markdown 注释），`max_retries=1`
- **THEN** `generate_and_parse` 以包含错误信息的修正 prompt 再次调用 `llm_call`，第二次返回合法 JSON，最终成功返回 DTO

#### Scenario: 重试 prompt 包含错误信息
- **WHEN** 首次解析失败，错误信息为 `"Expecting ',' delimiter: line 5 column 3"`
- **THEN** 重试 prompt 中包含该具体错误信息，便于 LLM 自修正

#### Scenario: 多次重试
- **WHEN** `max_retries=2`，首次和第一次重试均失败，第二次重试成功
- **THEN** 共调用 `llm_call` 三次，最终返回 DTO

### Requirement: 重试耗尽后抛出异常

当所有重试均失败时，`generate_and_parse` SHALL 抛出最后一次 `parse_llm_json_output` 产生的 `LLMJsonParseError`。

#### Scenario: 所有尝试均失败
- **WHEN** `max_retries=1`，首次和重试均返回非法 JSON
- **THEN** 抛出 `LLMJsonParseError`，`message` 和 `details` 来自最后一次解析失败

#### Scenario: max_retries 为 0 时不重试
- **WHEN** `max_retries=0`，首次返回非法 JSON
- **THEN** 仅调用 `llm_call` 一次，直接抛出 `LLMJsonParseError`

### Requirement: 重试过程经 LLM 调用审计

`generate_and_parse` 的每次 `llm_call` 调用（包括重试）SHALL 独立经过 `LLMService` 的调用审计链路。

#### Scenario: 重试产生独立审计记录
- **WHEN** `generate_and_parse` 首次失败后重试成功，共调用 `llm_call` 两次
- **THEN** `LLMCallLog` 中产生两条独立记录，每条包含各自的 prompt、completion、latency

### Requirement: 重试日志记录

`generate_and_parse` 在每次重试时 SHALL 记录 WARNING 级别日志，包含：重试次数、`context_label`、上一次的错误摘要。

#### Scenario: 重试时记录日志
- **WHEN** `generate_and_parse` 以 `context_label="估值建模师"` 调用，首次解析失败触发重试
- **THEN** WARNING 日志中包含 `"估值建模师"`、重试序号（如 `"第 1 次重试"`）、上一次错误摘要

### Requirement: LLM 调用异常透传

当 `llm_call` 本身抛出异常（如 `LLMConnectionError`、网络超时）时，`generate_and_parse` SHALL 直接向上透传该异常，不进行重试。

#### Scenario: LLM 连接失败不重试
- **WHEN** `llm_call` 首次调用抛出 `LLMConnectionError`
- **THEN** `generate_and_parse` 直接抛出 `LLMConnectionError`，不触发重试，`llm_call` 仅被调用一次

#### Scenario: 重试中 LLM 连接失败
- **WHEN** 首次解析失败触发重试，重试时 `llm_call` 抛出 `LLMConnectionError`
- **THEN** `generate_and_parse` 直接抛出 `LLMConnectionError`，不继续后续重试
