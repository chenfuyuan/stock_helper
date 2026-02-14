## Context

当前系统中 9 个 Agent 的 output_parser 分布在 3 个 Bounded Context（Research×5、Debate×3、Judge×1），每个 parser 独立实现相同的预处理管线：strip `<think>` → strip markdown code block → `json.loads` → Pydantic `model_validate`。实现质量参差不齐：

- **valuation_modeler**：使用 `normalize_llm_json_like_text`（含控制字符修复）+ `_extract_json_object_fallback`，最健壮。
- **macro_intelligence / catalyst_detective / technical_analyst**：各自实现 `_strip_thinking_tags` + 正则剥离 markdown，但无 fallback 提取、无控制字符修复。
- **financial_auditor / verdict / bull_advocate / bear_advocate / resolution**：最基础的 strip + loads，无额外容错。

三个模块各自定义了同名的 `LLMOutputParseError`（均继承 `AppException`），语义相同但类型独立。

`ILLMProvider` Port 签名为 `generate(prompt, system_message?, temperature?) -> str`，本方案不修改此签名。

## Goals / Non-Goals

**Goals:**
- 提供一个供应商无关、位于 `src/shared/` 的统一 LLM JSON 解析器，消除 9 个 parser 中的重复预处理与校验逻辑。
- 统一处理器内聚全部健壮性策略：think 标签剥离、markdown 代码块剥离、控制字符修复、JSON 对象 fallback 提取、Pydantic 校验。
- 提供带错误反馈的重试能力，内聚于处理器，不侵入 `ILLMProvider` 或 `LLMService`。
- 各 Agent 的 output_parser 重构为薄包装：仅声明目标 DTO 类型 + 可选的字段归一化钩子。

**Non-Goals:**
- 不修改 `ILLMProvider` Port 签名或 `LLMService` 实现。
- 不依赖任何 LLM 供应商特有能力（JSON Mode、Structured Outputs、Function Calling 等）。
- 不统一三个模块的 `LLMOutputParseError` 为单一类型（各模块保持自己的领域异常定义，统一处理器抛出的是通用异常，由各 parser 包装为模块专属异常）。
- 不改变现有 Agent Adapter 的调用流程（仍由 Adapter 调用 `generate` 再调 parser）。

## Decisions

### D1: 统一处理器放置于 `src/shared/infrastructure/llm_json_parser.py`

**选择**：`src/shared/infrastructure/`。

**理由**：
- 该处理器是纯技术关注点（文本清洗 + JSON 解析 + Pydantic 校验），不包含领域逻辑，属于 Infrastructure 层。
- `src/shared/` 是跨模块共享内核的标准位置（参见 vision-and-modules §4）。
- 不放在 `llm_platform` 模块中，因为处理器不依赖 LLM 平台的任何领域概念，且 `llm_platform` 的职责边界是"LLM 配置管理 + 多厂商路由 + Chat/Completion"（参见 vision-and-modules §3.2），JSON 解析不属于其职责。

**备选**：放在 `src/shared/domain/` —— 但它不是领域概念，是技术工具。

### D2: 纯函数 API 而非类

**选择**：提供两个模块级函数，不引入类。

```python
# 纯解析（同步），用于已有 raw 文本的场景
def parse_llm_json_output(
    raw: str,
    dto_type: type[T],
    *,
    normalizers: list[Callable[[dict], dict]] | None = None,
    context_label: str = "",
) -> T: ...

# 调用 + 解析 + 重试（异步），用于需要重试的场景
async def generate_and_parse(
    llm_call: Callable[..., Awaitable[str]],
    dto_type: type[T],
    *,
    prompt: str,
    system_message: str | None = None,
    temperature: float = 0.7,
    normalizers: list[Callable[[dict], dict]] | None = None,
    max_retries: int = 1,
    context_label: str = "",
) -> T: ...
```

**理由**：
- 函数比类更轻量，调用方无需实例化或依赖注入。
- `parse_llm_json_output` 是纯函数（无副作用），易于测试。
- `generate_and_parse` 接收 `llm_call` 回调而非 `ILLMProvider` 实例，保持与 Port 接口的松耦合——调用方可传入 `functools.partial(llm_service.generate, alias="xxx")` 或任何返回 `str` 的异步函数。

**备选**：封装为 `LLMJsonParser` 类 —— 无状态场景中类是多余的抽象，且会引入依赖注入的复杂度。

### D3: 预处理管线固定顺序

处理管线按以下固定顺序执行，不可配置：

1. **空值检查**：`raw` 为空或纯空白 → 立即抛异常
2. **Strip `<think>` 标签**：`re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)`
3. **Strip Markdown 代码块**：首个 ` ``` ` 到最后一个 ` ``` ` 之间的内容，自动去除 `json` 语言标识
4. **修复控制字符**：JSON 字符串值内的字面换行/回车/制表符 → 转义形式
5. **`json.loads`**：若失败，进入 fallback
6. **Fallback 提取**：从文本中提取首尾配对的 `{ }` 之间内容，再次 `json.loads`
7. **根节点类型检查**：必须为 `dict`
8. **归一化钩子**：依次执行 `normalizers`（各 Agent 特有的字段映射）
9. **Pydantic `model_validate`**：校验并反序列化为目标 DTO

**理由**：现有 9 个 parser 的管线本质相同，仅差在"有没有做某些步骤"。固定顺序可确保所有 Agent 获得一致的最高健壮性，无需各自选择。

### D4: 归一化钩子签名为 `Callable[[dict], dict]`

**选择**：钩子接收 `json.loads` 产出的 `dict`，返回归一化后的 `dict`，在 Pydantic 校验之前执行。

**理由**：
- 当前各 Agent 的特有逻辑（如 valuation_modeler 的 verdict 枚举映射、bull/bear_advocate 的 `supporting_arguments` 对象数组→字符串列表）都作用于 JSON dict 层面，在 Pydantic 校验之前。
- 钩子签名简单，各 Agent 的 output_parser 只需定义一个小函数即可。

### D5: 重试策略——将解析错误拼入 prompt 让 LLM 自修正

**选择**：`generate_and_parse` 在 `parse_llm_json_output` 失败时，构造包含错误摘要的修正 prompt，再次调用 `llm_call`。

重试 prompt 模板：
```
你上一次的输出无法解析为合法 JSON。
错误信息：{error_message}
请严格按要求重新输出，仅输出 JSON 对象，不要包含任何额外文字、Markdown 标记或代码块。
```

**理由**：
- 供应商无关：仅使用文本 prompt，不依赖任何 API 特性。
- 利用 LLM 的自修正能力，将具体错误反馈给模型，显著提高第二次输出的正确率。
- `max_retries` 默认 1（即最多调用 2 次 LLM），可由调用方按需调整。
- 重试时每次调用都经过 `LLMService.generate()`，自然被 `llm-call-audit` 审计，无需额外适配。

### D6: 异常策略——处理器抛通用异常，各模块 parser 包装为领域异常

**选择**：统一处理器抛出 `LLMJsonParseError`（定义在 `src/shared/domain/exceptions.py`，继承 `AppException`）。各 Agent 的 output_parser 薄包装中 `try/except LLMJsonParseError` 并转为模块自己的 `LLMOutputParseError`。

**理由**：
- 保持各 Bounded Context 的领域异常独立性（DDD 原则），不强制统一。
- 统一处理器作为 shared 基础设施，不应 import 或感知任何模块的领域异常。
- 转换代码极少（2-3 行），是合理的薄包装职责。

### D7: `research/infrastructure/llm_output_utils.py` 处理

**选择**：将其中的通用函数（`strip_thinking_tags`、`strip_markdown_code_block`、`_repair_control_chars_in_json_strings`、`normalize_llm_json_like_text`）迁移至 `src/shared/infrastructure/llm_json_parser.py` 的内部实现。原文件标记 deprecated 并保留至所有调用方迁移完毕后删除。

## Risks / Trade-offs

- **[重试增加延迟与成本]** → 默认 `max_retries=1`，最多多一次 LLM 调用。调用方可设为 0 禁用重试。对于时间敏感的场景（如实时查询），应显式设为 0。
- **[重试 prompt 可能打乱原始对话上下文]** → 重试时只发送修正指令 + 原始 prompt，不引入对话历史。当前 `ILLMProvider.generate` 是单轮调用，无需担心多轮上下文污染。
- **[归一化钩子可能引入 bug]** → 钩子由各 Agent 自行定义和测试。统一处理器对钩子做 try/except，钩子异常不吞没而是包装为 `LLMJsonParseError` 并附带原始 dict。
- **[迁移期间两套 parser 并存]** → 按 Agent 逐个迁移，每迁移一个即可独立测试验证。不做 big-bang 切换。
