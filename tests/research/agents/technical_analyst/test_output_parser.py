"""
任务 4.2：技术分析师输出解析测试（解析逻辑内聚于本 Agent）。
合法 JSON 解析后字段正确、signal 为三值之一、confidence ∈ [0,1]；
非 JSON 或缺字段时解析失败且不返回未校验字符串。
"""
import pytest

from src.modules.research.infrastructure.agents.technical_analyst.output_parser import (
    parse_technical_analysis_result,
)
from src.modules.research.domain.dtos.technical_analysis_dtos import TechnicalAnalysisResultDTO
from src.modules.research.domain.exceptions import LLMOutputParseError


def test_parse_valid_json_returns_dto_with_correct_fields():
    """合法 JSON 解析后字段正确，signal 为三值之一，confidence ∈ [0,1]。"""
    raw = '''{
        "signal": "BULLISH",
        "confidence": 0.85,
        "summary_reasoning": "RSI 进入超买区，均线多头排列",
        "key_technical_levels": {"support": 10.0, "resistance": 11.5},
        "risk_warning": "跌破 10 元支撑则观点失效"
    }'''
    result = parse_technical_analysis_result(raw)
    assert isinstance(result, TechnicalAnalysisResultDTO)
    assert result.signal == "BULLISH"
    assert result.confidence == 0.85
    assert result.summary_reasoning == "RSI 进入超买区，均线多头排列"
    assert result.key_technical_levels.support == 10.0
    assert result.key_technical_levels.resistance == 11.5
    assert result.risk_warning == "跌破 10 元支撑则观点失效"


def test_parse_valid_json_stripped_from_markdown_code_block():
    """Markdown 代码块包裹的 JSON 可正确剥离并解析。"""
    raw = """```json
{"signal": "NEUTRAL", "confidence": 0.5, "summary_reasoning": "x", "key_technical_levels": {"support": 0, "resistance": 0}, "risk_warning": ""}
```"""
    result = parse_technical_analysis_result(raw)
    assert result.signal == "NEUTRAL"
    assert result.confidence == 0.5


def test_parse_invalid_json_raises_and_does_not_return_raw():
    """非 JSON 时解析失败并抛出明确错误，不返回未校验字符串。"""
    with pytest.raises(LLMOutputParseError) as exc_info:
        parse_technical_analysis_result("not json at all")
    assert "JSON" in exc_info.value.message or "解析" in exc_info.value.message
    assert exc_info.value.code == "LLM_OUTPUT_PARSE_ERROR"


def test_parse_missing_required_field_raises():
    """缺少必填字段时解析失败并抛出明确错误。"""
    raw = '{"signal": "BULLISH", "confidence": 0.8}'
    with pytest.raises(LLMOutputParseError) as exc_info:
        parse_technical_analysis_result(raw)
    assert "必填" in exc_info.value.message or "校验" in exc_info.value.message or "契约" in exc_info.value.message


def test_parse_invalid_signal_raises():
    """signal 非三值之一时校验失败。"""
    raw = '''{"signal": "INVALID", "confidence": 0.5, "summary_reasoning": "", "key_technical_levels": {"support": 0, "resistance": 0}, "risk_warning": ""}'''
    with pytest.raises(LLMOutputParseError):
        parse_technical_analysis_result(raw)


def test_parse_confidence_out_of_range_raises():
    """confidence 超出 [0,1] 时校验失败。"""
    raw = '''{"signal": "NEUTRAL", "confidence": 1.5, "summary_reasoning": "", "key_technical_levels": {"support": 0, "resistance": 0}, "risk_warning": ""}'''
    with pytest.raises(LLMOutputParseError):
        parse_technical_analysis_result(raw)


def test_parse_empty_string_raises():
    """空字符串时抛出明确错误。"""
    with pytest.raises(LLMOutputParseError):
        parse_technical_analysis_result("")


def test_parse_narrative_report_present():
    """任务 12.7：JSON 含 narrative_report 时解析为 DTO 对应字段。"""
    raw = '''{
        "signal": "NEUTRAL",
        "confidence": 0.6,
        "summary_reasoning": "震荡",
        "key_technical_levels": {"support": 9.0, "resistance": 11.0},
        "risk_warning": "无",
        "narrative_report": "技术面中性，支撑 9 元、阻力 11 元，置信度 0.6。"
    }'''
    result = parse_technical_analysis_result(raw)
    assert result.narrative_report == "技术面中性，支撑 9 元、阻力 11 元，置信度 0.6。"


def test_parse_narrative_report_missing_defaults_to_empty():
    """任务 12.7：JSON 缺失 narrative_report 时解析为默认空字符串。"""
    raw = '''{
        "signal": "BULLISH",
        "confidence": 0.8,
        "summary_reasoning": "多头",
        "key_technical_levels": {"support": 10.0, "resistance": 12.0},
        "risk_warning": ""
    }'''
    result = parse_technical_analysis_result(raw)
    assert result.narrative_report == ""
