"""Resolution output_parser 单元测试：合法 JSON 解析成功、非法 JSON 抛 LLMOutputParseError。"""

import pytest

from src.modules.debate.domain.dtos.resolution_result import ResolutionResult
from src.modules.debate.domain.exceptions import LLMOutputParseError
from src.modules.debate.infrastructure.agents.resolution.output_parser import (
    parse_resolution_result,
)


def test_parse_valid_json_returns_resolution_result():
    """合法 JSON 解析为 ResolutionResult，含 risk_matrix。"""
    raw = """{
        "direction": "NEUTRAL",
        "confidence": 0.55,
        "bull_case_summary": "多头论点摘要",
        "bear_case_summary": "空头论点摘要",
        "risk_matrix": [
            {"risk": "政策风险", "probability": "中", "impact": "高", "mitigation": "分散持仓"}
        ],
        "key_disagreements": ["估值分歧"],
        "conflict_resolution": "综合裁决为中性"
    }"""
    result = parse_resolution_result(raw)
    assert isinstance(result, ResolutionResult)
    assert result.direction == "NEUTRAL"
    assert result.confidence == 0.55
    assert len(result.risk_matrix) == 1
    assert result.risk_matrix[0].risk == "政策风险"
    assert result.key_disagreements == ["估值分歧"]


def test_parse_invalid_json_raises_llm_output_parse_error():
    """非 JSON 时抛出 LLMOutputParseError。"""
    with pytest.raises(LLMOutputParseError):
        parse_resolution_result("not json")


def test_parse_empty_string_raises():
    """空字符串时抛出 LLMOutputParseError。"""
    with pytest.raises(LLMOutputParseError):
        parse_resolution_result("")
