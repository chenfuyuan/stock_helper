## Why

当前系统中 8 个 Agent 的 output_parser 均依赖 prompt 文字要求 LLM 输出 JSON，再通过 `json.loads` + Pydantic 校验解析。但 LLM 输出本质上不确定——常见问题包括：Markdown 代码块包裹、`<think>` 标签残留、字符串内未转义换行、JSON 前后附带说明文字、甚至完全非法的 JSON。各 parser 各自实现预处理逻辑且质量参差不齐（仅 valuation_modeler 有 fallback 提取和控制字符修复），解析失败即直接抛异常无重试机会。这导致研究流水线在生产中频繁因 `LLMOutputParseError` 中断。

## What Changes

- **新增统一泛型 LLM JSON 处理器**：在 `src/shared/` 中提供一个与 LLM 供应商无关的统一处理器，接受 LLM 原始输出字符串 + 目标 Pydantic DTO 类型，内聚全部预处理（think 标签剥离、Markdown 代码块剥离、控制字符修复、JSON 对象 fallback 提取）与 Pydantic 校验逻辑。支持可选的字段归一化钩子，供各 Agent 注入特有的后处理（如枚举映射）。
- **新增带错误反馈的重试能力**：统一处理器支持接收一个 LLM 回调函数（`Callable`），当解析失败时将错误信息拼入 prompt 自动重试，可配置最大重试次数。重试逻辑内聚在处理器中，不侵入 `ILLMProvider` 或 `LLMService`——调用方只需将已有的 `generate` 方法作为回调传入即可。
- **重构现有 output_parser**：将 Research（5 个）、Debate（3 个）、Judge（1 个）共 9 个 output_parser 迁移到统一处理器，各 parser 仅保留 agent 特有的归一化钩子（如 valuation_modeler 的 verdict 枚举映射、bull_advocate 的 supporting_arguments 归一化）。

**设计约束**：
1. **供应商无关**：方案不依赖任何 LLM 供应商的特有能力（如 OpenAI JSON Mode、Structured Outputs）。所有健壮性由处理器自身的预处理 + 重试机制保证。
2. **单一职责内聚**：JSON 解析能力集中在统一处理器中，不散落到 `LLMService`、`ILLMProvider` 或各 Agent 的调用方法中。`ILLMProvider` Port 签名保持不变。

## Capabilities

### New Capabilities
- `unified-llm-output-parser`: 供应商无关的统一泛型 LLM JSON 处理器——提供 `parse_llm_json_output[T](raw, dto_type, normalizers?) -> T` 纯解析函数，内聚全部预处理与 Pydantic 校验逻辑，替代 9 个模块各自重复的 output_parser 实现。支持可选归一化钩子供 Agent 注入特有后处理。
- `llm-json-retry`: 带错误反馈的 LLM JSON 重试能力——统一处理器提供 `generate_and_parse[T](llm_callback, dto_type, max_retries?) -> T`，封装 调用LLM → 解析 → 失败时带错误信息重试 的闭环。重试逻辑内聚于处理器，不修改 `ILLMProvider` 或 `LLMService` 接口。

### Modified Capabilities
（无。`ILLMProvider` Port 和 `LLMService` 接口均不变；`llm-call-audit` 行为不变——重试时每次 `generate` 调用自然经过 `LLMService` 审计。）

## Impact

- **src/shared/**：新增统一处理器模块（如 `src/shared/infrastructure/llm_json_parser.py`），承载预处理、解析、校验、重试全部逻辑。
- **llm_platform 模块**：**无变更**。`ILLMProvider` Port 签名和 `LLMService` 实现均保持不变。
- **research 模块**：5 个 agent output_parser 重构为薄包装（调用统一处理器 + 可选归一化钩子）；`llm_output_utils.py` 中的通用函数迁移至 shared 或标记 deprecated。
- **debate 模块**：3 个 agent output_parser 重构为薄包装。
- **judge 模块**：1 个 agent output_parser 重构为薄包装。
- **依赖**：无新外部依赖。
