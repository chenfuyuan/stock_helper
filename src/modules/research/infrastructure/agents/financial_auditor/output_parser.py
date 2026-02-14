"""
财务审计员 Agent 的 LLM 输出解析。

委托统一处理器完成预处理、JSON 解析与 Pydantic 校验，
本模块仅做 narrative_report 默认值补充、signal 一致性修正与异常类型转换。
"""

from src.modules.research.domain.dtos.financial_dtos import (
    FinancialAuditResultDTO,
    FinancialSignal,
)
from src.modules.research.domain.exceptions import LLMOutputParseError
from src.shared.domain.exceptions import LLMJsonParseError
from src.shared.infrastructure.llm_json_parser import parse_llm_json_output


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


def _ensure_signal_consistent(
    dto: FinancialAuditResultDTO,
) -> FinancialAuditResultDTO:
    """若 score 与 signal 不匹配，以 score 为准重新映射 signal。"""
    expected = _score_to_signal(dto.financial_score)
    if dto.signal != expected:
        return dto.model_copy(update={"signal": expected})
    return dto


def _default_narrative_report(data: dict) -> dict:
    """为缺少 narrative_report 字段的数据补充默认空字符串。"""
    data.setdefault("narrative_report", "")
    return data


def parse_financial_audit_result(raw: str) -> FinancialAuditResultDTO:
    """
    将财务审计员 LLM 返回的字符串解析为 FinancialAuditResultDTO。

    委托 parse_llm_json_output 完成全部预处理与校验，
    解析成功后按 financial_score 确保 signal 与评分区间一致。

    Raises:
        LLMOutputParseError: 解析失败时（空内容、非法 JSON、字段校验失败）
    """
    try:
        dto = parse_llm_json_output(
            raw,
            FinancialAuditResultDTO,
            normalizers=[_default_narrative_report],
            context_label="财务审计员",
        )
    except LLMJsonParseError as e:
        raise LLMOutputParseError(
            message=e.message,
            details=e.details,
        ) from e

    return _ensure_signal_consistent(dto)
