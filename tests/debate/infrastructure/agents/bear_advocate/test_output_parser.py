"""Bear Advocate output_parser 单元测试：合法 JSON 解析成功、非法 JSON 抛 LLMOutputParseError。"""

import pytest

from src.modules.debate.domain.dtos.bull_bear_argument import BearArgument
from src.modules.debate.domain.exceptions import LLMOutputParseError
from src.modules.debate.infrastructure.agents.bear_advocate.output_parser import (
    parse_bear_argument,
)


def test_parse_valid_json_returns_bear_argument():
    """合法 JSON 解析为 BearArgument，字段正确。"""
    raw = """{
        "direction": "BEARISH",
        "confidence": 0.7,
        "core_thesis": "估值偏高且宏观承压",
        "supporting_arguments": ["PE 分位高", "流动性收紧"],
        "acknowledged_strengths": ["业绩稳定"],
        "risk_triggers": ["政策收紧"]
    }"""
    result = parse_bear_argument(raw)
    assert isinstance(result, BearArgument)
    assert result.direction == "BEARISH"
    assert result.confidence == 0.7
    assert result.core_thesis == "估值偏高且宏观承压"
    assert len(result.acknowledged_strengths) == 1
    assert len(result.risk_triggers) == 1


def test_parse_invalid_json_raises_llm_output_parse_error():
    """非 JSON 时抛出 LLMOutputParseError。"""
    with pytest.raises(LLMOutputParseError):
        parse_bear_argument("not json")


def test_parse_empty_string_raises():
    """空字符串时抛出 LLMOutputParseError。"""
    with pytest.raises(LLMOutputParseError):
        parse_bear_argument("")
