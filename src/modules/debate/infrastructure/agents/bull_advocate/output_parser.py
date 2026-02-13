"""
Bull Advocate Agent 的 LLM 输出解析。

将 LLM 返回的 JSON 解析为 BullArgument DTO，失败时抛 LLMOutputParseError。
"""
import json
import re
from typing import Any, Union

from pydantic import ValidationError

from src.modules.debate.domain.dtos.bull_bear_argument import BullArgument
from src.modules.debate.domain.exceptions import LLMOutputParseError


def _strip_thinking_tags(text: str) -> str:
    """移除 <think>...</think> 标签及其内容。"""
    if "<think>" in text:
        return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
    return text


def parse_bull_argument(raw: str) -> BullArgument:
    """
    将 Bull Advocate LLM 返回的字符串解析为 BullArgument。
    若为 Markdown 代码块包裹的 JSON，先剥离再解析。
    非法 JSON 或校验失败时抛出 LLMOutputParseError。
    """
    if not raw or not raw.strip():
        raise LLMOutputParseError(message="LLM 返回内容为空", details={"raw_length": 0})

    text = raw.strip()
    text = _strip_thinking_tags(text)
    match = re.search(r"^```(?:json)?\s*\n?(.*?)\n?```\s*$", text, re.DOTALL)
    if match:
        text = match.group(1).strip()

    try:
        data: Union[dict, list] = json.loads(text)
    except json.JSONDecodeError as e:
        raise LLMOutputParseError(
            message="LLM 返回内容不是合法 JSON",
            details={"json_error": e.msg, "position": e.pos},
        ) from e

    if not isinstance(data, dict):
        raise LLMOutputParseError(message="LLM 返回 JSON 根节点须为对象", details={})

    try:
        return BullArgument.model_validate(data)
    except ValidationError as e:
        raise LLMOutputParseError(
            message=f"LLM 返回格式不符合 BullArgument 契约：{e}",
            details={"validation_errors": e.errors()},
        ) from e
