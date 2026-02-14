"""
Bear Advocate Agent 的 LLM 输出解析。

委托统一处理器完成预处理、JSON 解析与 Pydantic 校验，
本模块仅做 supporting_arguments / acknowledged_strengths / risk_triggers 归一化与异常类型转换。
"""

from typing import Any

from src.modules.debate.domain.dtos.bull_bear_argument import BearArgument
from src.modules.debate.domain.exceptions import LLMOutputParseError
from src.shared.domain.exceptions import LLMJsonParseError
from src.shared.infrastructure.llm_json_parser import parse_llm_json_output


def _normalize_supporting_arguments(val: Any) -> list[str]:
    """将 Prompt 返回的对象数组转为 list[str]，供 BearArgument.supporting_arguments 使用。"""
    if not isinstance(val, list):
        return []
    result: list[str] = []
    for item in val:
        if isinstance(item, str):
            result.append(item)
        elif isinstance(item, dict):
            arg = item.get("argument") or item.get("evidence") or ""
            dim = item.get("dimension", "")
            result.append(
                f"{dim}: {arg}".strip() if dim and arg else (arg or dim)
            )
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


def _normalize_bear_fields(data: dict) -> dict:
    """归一化空头辩护人特有字段：对象数组→字符串列表，补充 narrative_report 默认值。"""
    data["supporting_arguments"] = _normalize_supporting_arguments(
        data.get("supporting_arguments")
    )
    data["acknowledged_strengths"] = _normalize_string_list(
        data.get("acknowledged_strengths")
    )
    data["risk_triggers"] = _normalize_string_list(data.get("risk_triggers"))
    data.setdefault("narrative_report", "")
    return data


def parse_bear_argument(raw: str) -> BearArgument:
    """
    将 Bear Advocate LLM 返回的字符串解析为 BearArgument。

    委托 parse_llm_json_output 完成全部预处理与校验，
    通过归一化钩子处理 supporting_arguments 等字段。

    Raises:
        LLMOutputParseError: 解析失败时（空内容、非法 JSON、字段校验失败）
    """
    try:
        return parse_llm_json_output(
            raw,
            BearArgument,
            normalizers=[_normalize_bear_fields],
            context_label="空头辩护人",
        )
    except LLMJsonParseError as e:
        raise LLMOutputParseError(
            message=e.message,
            details=e.details,
        ) from e
