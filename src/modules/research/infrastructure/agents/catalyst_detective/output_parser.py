"""
催化剂侦探 Agent 的 LLM 输出解析。

委托统一处理器完成预处理、JSON 解析与 Pydantic 校验，
本模块仅做 narrative_report 默认值补充、异常类型转换与成功日志记录。
"""

from loguru import logger

from src.modules.research.domain.dtos.catalyst_dtos import (
    CatalystDetectiveResultDTO,
)
from src.modules.research.domain.exceptions import LLMOutputParseError
from src.shared.domain.exceptions import LLMJsonParseError
from src.shared.infrastructure.llm_json_parser import parse_llm_json_output


def _default_narrative_report(data: dict) -> dict:
    """为缺少 narrative_report 字段的数据补充默认空字符串。"""
    data.setdefault("narrative_report", "")
    return data


def parse_catalyst_detective_result(raw: str) -> CatalystDetectiveResultDTO:
    """
    将催化剂侦探 LLM 返回的字符串解析为 CatalystDetectiveResultDTO。

    委托 parse_llm_json_output 完成全部预处理与校验。

    Raises:
        LLMOutputParseError: 解析失败时（空内容、非法 JSON、字段校验失败）
    """
    try:
        dto = parse_llm_json_output(
            raw,
            CatalystDetectiveResultDTO,
            normalizers=[_default_narrative_report],
            context_label="催化剂侦探",
        )
    except LLMJsonParseError as e:
        raise LLMOutputParseError(
            message=e.message,
            details=e.details,
        ) from e

    logger.info(
        "催化剂侦探结果解析成功：catalyst_assessment={}，confidence_score={}，"
        "正面催化数={}，负面催化数={}，来源数={}",
        dto.catalyst_assessment,
        dto.confidence_score,
        len(dto.positive_catalysts),
        len(dto.negative_catalysts),
        len(dto.information_sources),
    )

    return dto
