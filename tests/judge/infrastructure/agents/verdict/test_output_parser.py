"""output_parser 单元测试：合法 JSON 解析为 VerdictResult 成功、非法 JSON 抛 LLMOutputParseError。"""

import pytest

from src.modules.judge.domain.dtos.verdict_result import VerdictResult
from src.modules.judge.domain.exceptions import LLMOutputParseError
from src.modules.judge.infrastructure.agents.verdict.output_parser import (
    parse_verdict_result,
)


def test_parse_valid_json_returns_verdict_result():
    """合法 JSON 解析为 VerdictResult。"""
    raw = """{
        "action": "BUY",
        "position_percent": 0.3,
        "confidence": 0.72,
        "entry_strategy": "分批建仓",
        "stop_loss": "-5%",
        "take_profit": "+15%",
        "time_horizon": "3-6个月",
        "risk_warnings": ["流动性风险", "政策风险"],
        "reasoning": "综合辩论结论偏多，建议轻仓参与"
    }"""
    result = parse_verdict_result(raw)
    assert isinstance(result, VerdictResult)
    assert result.action == "BUY"
    assert result.position_percent == 0.3
    assert result.confidence == 0.72
    assert len(result.risk_warnings) == 2
    assert "流动性风险" in result.risk_warnings


def test_parse_invalid_json_raises_llm_output_parse_error():
    """非 JSON 时抛出 LLMOutputParseError。"""
    with pytest.raises(LLMOutputParseError):
        parse_verdict_result("not json")


def test_parse_empty_string_raises():
    """空字符串时抛出 LLMOutputParseError。"""
    with pytest.raises(LLMOutputParseError):
        parse_verdict_result("")
