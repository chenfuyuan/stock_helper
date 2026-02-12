"""
估值建模师 Agent 的 LLM 输出解析。
将本 Agent 返回的 JSON 字符串解析为 ValuationResultDTO，内聚于该 Agent。
非法 JSON 或缺字段时记录日志（含 LLM 原始输出，便于排查）并抛出 LLMOutputParseError。
支持 ```json 包裹与 <think> 标签剥离。
"""
import json
import re
from typing import Any, Union

from loguru import logger
from pydantic import ValidationError

from src.modules.research.domain.valuation_dtos import ValuationResultDTO
from src.modules.research.domain.exceptions import LLMOutputParseError

_RAW_LOG_MAX_LEN = 2000


def _raw_for_log(raw: str) -> str:
    """返回用于日志的原始内容，过长时截断。"""
    if not raw:
        return "(空)"
    s = raw.strip()
    if len(s) <= _RAW_LOG_MAX_LEN:
        return s
    return s[:_RAW_LOG_MAX_LEN] + f"...[已截断，总长 {len(s)} 字符]"


def _strip_thinking_tags(text: str) -> str:
    """
    移除 reasoning model 输出的 <think>...</think> 标签及其内容。
    部分思考模型（如 DeepSeek R1）会在响应前输出推理过程，需剥离后才能解析 JSON。
    """
    if "<think>" in text:
        logger.debug("检测到 <think> 标签，正在剥离 reasoning model 的思考过程")
        return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
    return text


def _format_validation_errors(errors: list[dict[str, Any]]) -> str:
    """将 Pydantic 校验错误格式化为可读摘要。"""
    parts = []
    for err in errors:
        loc = ".".join(str(x) for x in err.get("loc", ()))
        msg = err.get("msg", "")
        inp = err.get("input")
        if inp is None:
            actual = "None/缺失"
        elif isinstance(inp, list):
            actual = f"list (长度 {len(inp)})"
        elif isinstance(inp, dict):
            actual = f"dict (键: {list(inp.keys())[:5]})"
        else:
            actual = f"{type(inp).__name__} ({repr(inp)[:50]})"
        parts.append(f"字段 {loc}：{msg}，实际：{actual}")
    return "；".join(parts)


def parse_valuation_result(raw: str) -> ValuationResultDTO:
    """
    将估值建模师 LLM 返回的字符串解析为 ValuationResultDTO。
    若为 Markdown 代码块包裹的 JSON，先剥离再解析。
    支持剥离 <think>...</think> 标签（reasoning model 的思考过程）。
    非法 JSON 或校验失败时记录日志（含 LLM 原始输出）并抛出 LLMOutputParseError。
    """
    if not raw or not raw.strip():
        logger.warning(
            "解析估值建模结果：LLM 返回为空，raw={}", _raw_for_log(raw or "")
        )
        raise LLMOutputParseError(
            message="LLM 返回内容为空", details={"raw_length": 0}
        )

    text = raw.strip()
    # 移除 reasoning model 的 <think>...</think> 标签
    text = _strip_thinking_tags(text)
    # 剥离 ```json ... ``` 或 ``` ... ```
    match = re.search(r"^```(?:json)?\s*\n?(.*?)\n?```\s*$", text, re.DOTALL)
    if match:
        text = match.group(1).strip()

    try:
        data: Union[dict, list] = json.loads(text)
    except json.JSONDecodeError as e:
        logger.warning(
            "解析估值建模结果：非合法 JSON，msg={}，LLM 原始输出：{}",
            e.msg,
            _raw_for_log(raw),
        )
        raise LLMOutputParseError(
            message="LLM 返回内容不是合法 JSON",
            details={"json_error": e.msg, "position": e.pos},
        ) from e

    if not isinstance(data, dict):
        logger.warning(
            "解析估值建模结果：JSON 根节点非对象，LLM 原始输出：{}",
            _raw_for_log(raw),
        )
        raise LLMOutputParseError(
            message="LLM 返回 JSON 根节点须为对象", details={}
        )

    try:
        dto = ValuationResultDTO.model_validate(data)
    except ValidationError as e:
        summary = _format_validation_errors(e.errors())
        logger.warning(
            "解析估值建模结果：字段校验失败。详情：{} | LLM 原始输出：{}",
            summary,
            _raw_for_log(raw),
        )
        raise LLMOutputParseError(
            message=f"LLM 返回格式不符合估值建模结果契约：{summary}",
            details={"validation_errors": e.errors(), "summary": summary},
        ) from e

    return dto
