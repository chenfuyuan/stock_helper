"""
估值建模师 Agent 的 LLM 输出解析。
将本 Agent 返回的 JSON 字符串解析为 ValuationResultDTO，内聚于该 Agent。
非法 JSON 或缺字段时记录日志（含 LLM 原始输出，便于排查）并抛出 LLMOutputParseError。
支持 ```json 包裹、<think> 标签剥离；解析失败时尝试提取首尾 { } 间内容再解析。
"""
import json
from typing import Any, Union

from loguru import logger
from pydantic import ValidationError

from src.modules.research.domain.dtos.valuation_dtos import ValuationResultDTO
from src.modules.research.domain.exceptions import LLMOutputParseError
from src.modules.research.infrastructure.llm_output_utils import (
    normalize_llm_json_like_text,
)

_RAW_LOG_MAX_LEN = 2000

# LLM 可能返回英文或「英文 (中文)」格式，归一化为英文枚举以通过契约校验
_VERDICT_NORMALIZE_MAP: dict[str, str] = {
    "Undervalued": "Undervalued",
    "Undervalued (低估)": "Undervalued",
    "Fair": "Fair",
    "Fair (合理)": "Fair",
    "Overvalued": "Overvalued",
    "Overvalued (高估)": "Overvalued",
}


def _raw_for_log(raw: str) -> str:
    """返回用于日志的原始内容，过长时截断。"""
    if not raw:
        return "(空)"
    s = raw.strip()
    if len(s) <= _RAW_LOG_MAX_LEN:
        return s
    return s[:_RAW_LOG_MAX_LEN] + f"...[已截断，总长 {len(s)} 字符]"


def _extract_json_object_fallback(text: str) -> str | None:
    """
    当 json.loads 失败时，尝试提取首尾成对的 { } 之间的内容再解析。
    适用于 LLM 在 JSON 前后加了说明文字的情况；若内容中字符串含未转义 " 则可能仍失败。
    """
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    in_string = False
    escape = False
    quote_char = None
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
            elif c in ('"', "'"):
                in_string = True
                quote_char = c
            i += 1
            continue
        if c == quote_char:
            in_string = False
        i += 1
    return None


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

    text = normalize_llm_json_like_text(raw)
    if not text:
        logger.warning(
            "解析估值建模结果：预处理后为空，raw={}", _raw_for_log(raw or "")
        )
        raise LLMOutputParseError(
            message="LLM 返回内容为空", details={"raw_length": len(raw or "")}
        )

    data: Union[dict, list] | None = None
    last_error: json.JSONDecodeError | None = None
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        last_error = e
        extracted = _extract_json_object_fallback(text)
        if extracted and extracted != text:
            try:
                data = json.loads(extracted)
            except json.JSONDecodeError:
                pass
    if data is None and last_error is not None:
        logger.warning(
            "解析估值建模结果：非合法 JSON，msg={}，position={}，LLM 原始输出：{}",
            last_error.msg,
            last_error.pos,
            _raw_for_log(raw),
        )
        raise LLMOutputParseError(
            message="LLM 返回内容不是合法 JSON",
            details={"json_error": last_error.msg, "position": last_error.pos},
        ) from last_error

    if not isinstance(data, dict):
        logger.warning(
            "解析估值建模结果：JSON 根节点非对象，LLM 原始输出：{}",
            _raw_for_log(raw),
        )
        raise LLMOutputParseError(
            message="LLM 返回 JSON 根节点须为对象", details={}
        )

    data.setdefault("narrative_report", "")
    # 归一化 valuation_verdict：接受英文或「英文 (中文)」，统一为英文以通过契约
    raw_verdict = data.get("valuation_verdict")
    if isinstance(raw_verdict, str) and raw_verdict.strip():
        normalized = _VERDICT_NORMALIZE_MAP.get(raw_verdict.strip())
        if normalized is not None:
            data["valuation_verdict"] = normalized
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
