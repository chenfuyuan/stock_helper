"""
统一泛型 LLM JSON 处理器。

供应商无关，内聚全部 LLM 输出预处理、JSON 解析、Pydantic 校验与可选重试逻辑。
各模块 Agent 的 output_parser 应委托本模块的函数完成解析，仅保留 Agent 特有的归一化钩子。

预处理管线（固定顺序）：
1. 空值检查
2. 剥离 <think>...</think> 标签
3. 剥离 Markdown 代码块
4. 修复 JSON 字符串值内未转义的控制字符
5. json.loads
6. Fallback：提取首尾配对的 { } 再解析
7. 根节点类型检查（必须为 dict）
8. 归一化钩子
9. Pydantic model_validate
"""

import json
import re
from collections.abc import Awaitable, Callable
from typing import TypeVar

from loguru import logger
from pydantic import BaseModel, ValidationError

from src.shared.domain.exceptions import LLMJsonParseError

T = TypeVar("T", bound=BaseModel)

_RAW_LOG_MAX_LEN = 2000


# ---------------------------------------------------------------------------
# 内部预处理函数
# ---------------------------------------------------------------------------


def _raw_for_log(raw: str) -> str:
    """返回用于日志的原始内容，过长时截断。"""
    if not raw:
        return "(空)"
    s = raw.strip()
    if len(s) <= _RAW_LOG_MAX_LEN:
        return s
    return s[:_RAW_LOG_MAX_LEN] + f"...[已截断，总长 {len(s)} 字符]"


def _label(context_label: str) -> str:
    """格式化上下文标签，用于日志前缀。"""
    return f"[{context_label}] " if context_label else ""


def _strip_thinking_tags(text: str) -> str:
    """
    移除 reasoning model 输出的 <think>...</think> 标签及其内容。
    部分思考模型（如 DeepSeek R1）会在响应前输出推理过程，需剥离后再解析 JSON。
    """
    if "<think>" not in text:
        return text
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


def _strip_markdown_code_block(text: str) -> str:
    """
    剥离 Markdown 代码块（```json 或 ``` 包裹的内容）。
    按「首个开块到最后一个闭块」取内容，允许末尾有多余空白。
    """
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped
    first = stripped.find("```")
    last = stripped.rfind("```")
    if last <= first:
        return stripped
    content = stripped[first + 3 : last].strip()
    if content.lower().startswith("json"):
        content = content[4:].lstrip("\r\n\t ")
    return content.strip()


def _repair_control_chars_in_json_strings(text: str) -> str:
    """
    在 JSON 字符串值内部，将未转义的控制字符（换行、回车、制表等）转为转义形式。
    JSON 规范不允许字符串内出现字面 \\n/\\r/\\t，LLM 常直接输出字面换行导致 json.loads 失败。
    """
    result: list[str] = []
    i = 0
    in_string = False
    escape = False
    quote_char: str | None = None
    while i < len(text):
        c = text[i]
        if not in_string:
            result.append(c)
            if c == '"':
                in_string = True
                quote_char = c
            i += 1
            continue
        if escape:
            result.append(c)
            escape = False
            i += 1
            continue
        if c == "\\":
            result.append(c)
            escape = True
            i += 1
            continue
        if c == quote_char:
            result.append(c)
            in_string = False
            quote_char = None
            i += 1
            continue
        if c == "\n":
            result.append("\\n")
        elif c == "\r":
            result.append("\\r")
        elif c == "\t":
            result.append("\\t")
        elif ord(c) < 32 and c != " ":
            result.append("\\u%04x" % ord(c))
        else:
            result.append(c)
        i += 1
    return "".join(result)


def _extract_json_object_fallback(text: str) -> str | None:
    """
    当 json.loads 失败时，尝试提取首尾成对的 { } 之间的内容再解析。
    适用于 LLM 在 JSON 前后加了说明文字的情况。
    """
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    in_string = False
    escape = False
    i = start
    while i < len(text):
        c = text[i]
        if escape:
            escape = False
            i += 1
            continue
        if c == "\\" and in_string:
            escape = True
            i += 1
            continue
        if not in_string:
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    return text[start : i + 1]
            elif c == '"':
                in_string = True
            i += 1
            continue
        if c == '"':
            in_string = False
        i += 1
    return None


# ---------------------------------------------------------------------------
# 公开 API
# ---------------------------------------------------------------------------


def parse_llm_json_output(
    raw: str,
    dto_type: type[T],
    *,
    normalizers: list[Callable[[dict], dict]] | None = None,
    context_label: str = "",
) -> T:
    """
    将 LLM 原始输出字符串解析为指定的 Pydantic DTO 实例。

    按固定管线执行预处理：空值检查 → strip think → strip markdown →
    修复控制字符 → json.loads → fallback 提取 → 根节点检查 → 归一化钩子 → Pydantic 校验。

    Args:
        raw: LLM 原始返回字符串。
        dto_type: 目标 Pydantic BaseModel 子类。
        normalizers: 可选归一化钩子列表，在 json.loads 之后、Pydantic 校验之前依次执行。
                     每个钩子接收 dict 返回 dict。
        context_label: 上下文标签（如 "宏观情报员"），用于日志定位。

    Returns:
        解析并校验后的 DTO 实例。

    Raises:
        LLMJsonParseError: 任一阶段失败时抛出，携带错误详情。
    """
    prefix = _label(context_label)

    # 1. 空值检查
    if not raw or not raw.strip():
        logger.warning(
            "{}LLM 返回为空，raw_length={}", prefix, len(raw) if raw else 0
        )
        raise LLMJsonParseError(
            message="LLM 返回内容为空",
            details={"raw_length": len(raw) if raw else 0},
        )

    text = raw.strip()

    # 2. 剥离 <think>...</think> 标签
    text = _strip_thinking_tags(text)

    # 3. 剥离 Markdown 代码块
    text = _strip_markdown_code_block(text)

    # 4. 修复控制字符
    text = _repair_control_chars_in_json_strings(text)

    # 5. json.loads（+ 6. fallback 提取）
    data: dict | list | None = None
    last_json_error: json.JSONDecodeError | None = None
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        last_json_error = e
        # 6. Fallback：提取首尾配对的 { }
        extracted = _extract_json_object_fallback(text)
        if extracted and extracted != text:
            try:
                data = json.loads(extracted)
            except json.JSONDecodeError:
                pass

    if data is None:
        error_msg = (
            last_json_error.msg if last_json_error else "未知 JSON 错误"
        )
        error_pos = last_json_error.pos if last_json_error else None
        logger.warning(
            "{}LLM 返回非合法 JSON，error={}，LLM 原始输出：{}",
            prefix,
            error_msg,
            _raw_for_log(raw),
        )
        raise LLMJsonParseError(
            message="LLM 返回内容不是合法 JSON",
            details={
                "raw_length": len(raw),
                "json_error": error_msg,
                "position": error_pos,
            },
        ) from last_json_error

    # 7. 根节点类型检查
    if not isinstance(data, dict):
        logger.warning(
            "{}LLM 返回 JSON 根节点非对象，LLM 原始输出：{}",
            prefix,
            _raw_for_log(raw),
        )
        raise LLMJsonParseError(
            message="LLM 返回 JSON 根节点须为对象",
            details={"raw_length": len(raw)},
        )

    # 8. 归一化钩子
    if normalizers:
        for hook in normalizers:
            try:
                data = hook(data)
            except Exception as e:
                logger.warning(
                    "{}归一化钩子执行异常：{}，原始 dict 摘要：{}",
                    prefix,
                    e,
                    str(data)[:500],
                )
                raise LLMJsonParseError(
                    message=f"归一化钩子执行异常：{e}",
                    details={
                        "normalizer_error": str(e),
                        "raw_length": len(raw),
                    },
                ) from e

    # 9. Pydantic model_validate
    try:
        return dto_type.model_validate(data)
    except ValidationError as e:
        errors_summary = "; ".join(
            f"{'.'.join(str(x) for x in err.get('loc', ()))}: {err.get('msg', '')}"
            for err in e.errors()
        )
        logger.warning(
            "{}Pydantic 校验失败：{} | LLM 原始输出：{}",
            prefix,
            errors_summary,
            _raw_for_log(raw),
        )
        raise LLMJsonParseError(
            message=f"LLM 返回格式不符合契约：{errors_summary}",
            details={
                "raw_length": len(raw),
                "validation_errors": e.errors(),
            },
        ) from e


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
) -> T:
    """
    调用 LLM 并解析返回的 JSON 为 Pydantic DTO，解析失败时带错误反馈重试。

    重试逻辑内聚于本函数，不修改 ILLMProvider 或 LLMService 接口。
    每次 llm_call 调用自然经过 LLMService 审计，无需额外适配。
    LLM 调用异常（如 LLMConnectionError）直接透传，不触发重试。

    Args:
        llm_call: LLM 回调函数，签名兼容 (prompt, system_message, temperature) -> str。
        dto_type: 目标 Pydantic BaseModel 子类。
        prompt: 原始 prompt。
        system_message: 可选 system message。
        temperature: 采样温度，默认 0.7。
        normalizers: 可选归一化钩子列表。
        max_retries: 最大重试次数，默认 1（即最多调用 LLM 2 次）。设为 0 禁用重试。
        context_label: 上下文标签，用于日志定位。

    Returns:
        解析并校验后的 DTO 实例。

    Raises:
        LLMJsonParseError: 所有尝试均解析失败时抛出最后一次的错误。
        Exception: llm_call 本身的异常直接透传（如 LLMConnectionError）。
    """
    prefix = _label(context_label)
    current_prompt = prompt
    last_error: LLMJsonParseError | None = None

    for attempt in range(1 + max_retries):
        # 调用 LLM（异常直接透传，不重试）
        raw = await llm_call(current_prompt, system_message, temperature)

        try:
            return parse_llm_json_output(
                raw,
                dto_type,
                normalizers=normalizers,
                context_label=context_label,
            )
        except LLMJsonParseError as e:
            last_error = e
            remaining = max_retries - attempt
            if remaining <= 0:
                break
            # 构造含错误信息的修正 prompt
            logger.warning(
                "{}第 {} 次尝试解析失败，剩余重试 {} 次。错误：{}",
                prefix,
                attempt + 1,
                remaining,
                e.message,
            )
            current_prompt = (
                f"{prompt}\n\n"
                f"---\n"
                f"你上一次的输出无法解析为合法 JSON。\n"
                f"错误信息：{e.message}\n"
                f"请严格按要求重新输出，仅输出 JSON 对象，"
                f"不要包含任何额外文字、Markdown 标记或代码块。"
            )

    # 所有尝试均失败
    assert last_error is not None
    raise last_error
