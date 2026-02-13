"""
财务审计员 Agent 的 LLM 输出解析。
将本 Agent 返回的 JSON 字符串解析为 FinancialAuditResultDTO，内聚于该 Agent。
非法 JSON 或缺字段时记录日志（含 LLM 原始输出，便于排查）并抛出 LLMOutputParseError。
若 financial_score 与 signal 不符合评分区间映射，以 score 为准重新映射 signal。
"""
import json
import re
from typing import Any, Union

from loguru import logger
from pydantic import ValidationError

from src.modules.research.domain.dtos.financial_dtos import (
    FinancialAuditResultDTO,
    FinancialSignal,
)
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


def _score_to_signal(score: int) -> FinancialSignal:
    """按评分区间映射为 signal。90–100=STRONG_BULLISH，75–89=BULLISH，50–74=NEUTRAL，30–49=BEARISH，0–29=STRONG_BEARISH。"""
    if score >= 90:
        return "STRONG_BULLISH"
    if score >= 75:
        return "BULLISH"
    if score >= 50:
        return "NEUTRAL"
    if score >= 30:
        return "BEARISH"
    return "STRONG_BEARISH"


def _ensure_signal_consistent(dto: FinancialAuditResultDTO) -> FinancialAuditResultDTO:
    """若 score 与 signal 不匹配，以 score 为准重新映射 signal。"""
    expected = _score_to_signal(dto.financial_score)
    if dto.signal != expected:
        return dto.model_copy(update={"signal": expected})
    return dto


def parse_financial_audit_result(raw: str) -> FinancialAuditResultDTO:
    """
    将财务审计员 LLM 返回的字符串解析为 FinancialAuditResultDTO。
    若为 Markdown 代码块包裹的 JSON，先剥离再解析。
    非法 JSON 或校验失败时记录日志（含 LLM 原始输出）并抛出 LLMOutputParseError。
    解析成功后按 financial_score 确保 signal 与评分区间一致。
    """
    if not raw or not raw.strip():
        logger.warning(
            "解析财务审计结果：LLM 返回为空，raw={}", _raw_for_log(raw or "")
        )
        raise LLMOutputParseError(
            message="LLM 返回内容为空", details={"raw_length": 0}
        )

    text = raw.strip()
    match = re.search(r"^```(?:json)?\s*\n?(.*?)\n?```\s*$", text, re.DOTALL)
    if match:
        text = match.group(1).strip()

    try:
        data: Union[dict, list] = json.loads(text)
    except json.JSONDecodeError as e:
        logger.warning(
            "解析财务审计结果：非合法 JSON，msg={}，LLM 原始输出：{}",
            e.msg,
            _raw_for_log(raw),
        )
        raise LLMOutputParseError(
            message="LLM 返回内容不是合法 JSON",
            details={"json_error": e.msg, "position": e.pos},
        ) from e

    if not isinstance(data, dict):
        logger.warning(
            "解析财务审计结果：JSON 根节点非对象，LLM 原始输出：{}",
            _raw_for_log(raw),
        )
        raise LLMOutputParseError(
            message="LLM 返回 JSON 根节点须为对象", details={}
        )

    data.setdefault("narrative_report", "")
    try:
        dto = FinancialAuditResultDTO.model_validate(data)
    except ValidationError as e:
        summary = _format_validation_errors(e.errors())
        logger.warning(
            "解析财务审计结果：字段校验失败。详情：{} | LLM 原始输出：{}",
            summary,
            _raw_for_log(raw),
        )
        raise LLMOutputParseError(
            message=f"LLM 返回格式不符合财务审计结果契约：{summary}",
            details={"validation_errors": e.errors(), "summary": summary},
        ) from e

    return _ensure_signal_consistent(dto)
