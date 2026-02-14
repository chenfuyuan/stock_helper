"""
技术分析师 Agent 的 LLM 输出解析。

委托统一处理器完成预处理、JSON 解析与 Pydantic 校验，
本模块仅做 narrative_report 默认值补充与异常类型转换。
"""

from src.modules.research.domain.dtos.technical_analysis_dtos import (
    TechnicalAnalysisResultDTO,
)
from src.modules.research.domain.exceptions import LLMOutputParseError
from src.shared.domain.exceptions import LLMJsonParseError
from src.shared.infrastructure.llm_json_parser import parse_llm_json_output


def _default_narrative_report(data: dict) -> dict:
    """为缺少 narrative_report 字段的数据补充默认空字符串。"""
    data.setdefault("narrative_report", "")
    return data


def parse_technical_analysis_result(raw: str) -> TechnicalAnalysisResultDTO:
    """
    将技术分析师 LLM 返回的字符串解析为 TechnicalAnalysisResultDTO。

    委托 parse_llm_json_output 完成全部预处理与校验。

    Raises:
        LLMOutputParseError: 解析失败时（空内容、非法 JSON、字段校验失败）
    """
    try:
        return parse_llm_json_output(
            raw,
            TechnicalAnalysisResultDTO,
            normalizers=[_default_narrative_report],
            context_label="技术分析师",
        )
    except LLMJsonParseError as e:
        raise LLMOutputParseError(
            message=e.message,
            details=e.details,
        ) from e
