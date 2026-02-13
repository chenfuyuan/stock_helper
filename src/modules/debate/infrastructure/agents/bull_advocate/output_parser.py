"""
Bull Advocate Agent 的 LLM 输出解析。

将 LLM 返回的 JSON 解析为 BullArgument DTO，失败时抛 LLMOutputParseError。
Prompt 要求 supporting_arguments 为对象数组（dimension/argument/evidence/strength），
DTO 为 list[str]，解析前将对象数组规范化为字符串列表。
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


def _normalize_supporting_arguments(val: Any) -> list[str]:
    """将 Prompt 返回的对象数组转为 list[str]，供 BullArgument.supporting_arguments 使用。"""
    if not isinstance(val, list):
        return []
    result: list[str] = []
    for item in val:
        if isinstance(item, str):
            result.append(item)
        elif isinstance(item, dict):
            # Prompt 格式: {"dimension": "...", "argument": "...", "evidence": "...", "strength": "..."}
            arg = item.get("argument") or item.get("evidence") or ""
            dim = item.get("dimension", "")
            result.append(f"{dim}: {arg}".strip() if dim and arg else (arg or dim))
        else:
            result.append(str(item))
    return result


def _normalize_string_list(val: Any) -> list[str]:
    """确保为 list[str]，缺失或 null 返回 []。"""
    if val is None:
        return []
    if not isinstance(val, list):
        return [str(val)] if val else []
    return [str(x) for x in val]


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

    # Prompt 要求 supporting_arguments 为对象数组，DTO 为 list[str]，此处做归一化
    normalized = dict(data)
    normalized["supporting_arguments"] = _normalize_supporting_arguments(
        normalized.get("supporting_arguments")
    )
    normalized["acknowledged_risks"] = _normalize_string_list(
        normalized.get("acknowledged_risks")
    )
    normalized["price_catalysts"] = _normalize_string_list(
        normalized.get("price_catalysts")
    )
    normalized.setdefault("narrative_report", "")

    try:
        return BullArgument.model_validate(normalized)
    except ValidationError as e:
        raise LLMOutputParseError(
            message=f"LLM 返回格式不符合 BullArgument 契约：{e}",
            details={"validation_errors": e.errors()},
        ) from e
