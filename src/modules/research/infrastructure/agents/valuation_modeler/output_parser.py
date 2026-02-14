"""
估值建模师 Agent 的 LLM 输出解析。

委托统一处理器完成预处理、JSON 解析与 Pydantic 校验，
本模块仅做 verdict 枚举归一化、narrative_report 默认值与异常类型转换。
"""

from src.modules.research.domain.dtos.valuation_dtos import ValuationResultDTO
from src.modules.research.domain.exceptions import LLMOutputParseError
from src.shared.domain.exceptions import LLMJsonParseError
from src.shared.infrastructure.llm_json_parser import parse_llm_json_output

# LLM 可能返回英文或「英文 (中文)」格式，归一化为英文枚举以通过契约校验
_VERDICT_NORMALIZE_MAP: dict[str, str] = {
    "Undervalued": "Undervalued",
    "Undervalued (低估)": "Undervalued",
    "Fair": "Fair",
    "Fair (合理)": "Fair",
    "Overvalued": "Overvalued",
    "Overvalued (高估)": "Overvalued",
}


def _normalize_verdict(data: dict) -> dict:
    """
    归一化 valuation_verdict 字段：接受英文或「英文 (中文)」格式，统一为英文枚举值。
    同时为缺少 narrative_report 字段的数据补充默认空字符串。
    """
    data.setdefault("narrative_report", "")
    raw_verdict = data.get("valuation_verdict")
    if isinstance(raw_verdict, str) and raw_verdict.strip():
        normalized = _VERDICT_NORMALIZE_MAP.get(raw_verdict.strip())
        if normalized is not None:
            data["valuation_verdict"] = normalized
    return data


def parse_valuation_result(raw: str) -> ValuationResultDTO:
    """
    将估值建模师 LLM 返回的字符串解析为 ValuationResultDTO。

    委托 parse_llm_json_output 完成全部预处理与校验，
    通过归一化钩子处理 verdict 枚举映射。

    Raises:
        LLMOutputParseError: 解析失败时（空内容、非法 JSON、字段校验失败）
    """
    try:
        return parse_llm_json_output(
            raw,
            ValuationResultDTO,
            normalizers=[_normalize_verdict],
            context_label="估值建模师",
        )
    except LLMJsonParseError as e:
        raise LLMOutputParseError(
            message=e.message,
            details=e.details,
        ) from e
