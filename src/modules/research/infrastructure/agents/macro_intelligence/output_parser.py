"""
宏观情报员 Agent 的 LLM 输出解析。

委托统一处理器完成预处理、JSON 解析与 Pydantic 校验，
本模块仅做异常类型转换与成功日志记录。
"""

from loguru import logger

from src.modules.research.domain.dtos.macro_dtos import MacroIntelligenceResultDTO
from src.modules.research.domain.exceptions import LLMOutputParseError
from src.shared.domain.exceptions import LLMJsonParseError
from src.shared.infrastructure.llm_json_parser import parse_llm_json_output


def _default_narrative_report(data: dict) -> dict:
    """为缺少 narrative_report 字段的数据补充默认空字符串。"""
    data.setdefault("narrative_report", "")
    return data


def parse_macro_intelligence_result(raw: str) -> MacroIntelligenceResultDTO:
    """
    将宏观情报员 LLM 返回的字符串解析为 MacroIntelligenceResultDTO。

    委托 parse_llm_json_output 完成全部预处理与校验，
    捕获 LLMJsonParseError 转为 research 模块的 LLMOutputParseError。

    Args:
        raw: LLM 原始返回字符串

    Returns:
        MacroIntelligenceResultDTO: 解析后的宏观分析结果

    Raises:
        LLMOutputParseError: 解析失败时（空内容、非法 JSON、字段校验失败）
    """
    try:
        dto = parse_llm_json_output(
            raw,
            MacroIntelligenceResultDTO,
            normalizers=[_default_narrative_report],
            context_label="宏观情报员",
        )
    except LLMJsonParseError as e:
        raise LLMOutputParseError(
            message=e.message, details=e.details,
        ) from e

    logger.info(
        "宏观情报结果解析成功：macro_environment={}，confidence_score={}，"
        "维度分析数={}，机会数={}，风险数={}，来源数={}",
        dto.macro_environment,
        dto.confidence_score,
        len(dto.dimension_analyses),
        len(dto.key_opportunities),
        len(dto.key_risks),
        len(dto.information_sources),
    )

    return dto
