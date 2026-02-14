"""Bull Advocate output_parser 单元测试：合法 JSON 解析成功、非法 JSON 抛 LLMOutputParseError。"""

import pytest

from src.modules.debate.domain.dtos.bull_bear_argument import BullArgument
from src.modules.debate.domain.exceptions import LLMOutputParseError
from src.modules.debate.infrastructure.agents.bull_advocate.output_parser import (
    parse_bull_argument,
)


def test_parse_valid_json_returns_bull_argument():
    """合法 JSON 解析为 BullArgument，字段正确。"""
    raw = """{
        "direction": "BULLISH",
        "confidence": 0.75,
        "core_thesis": "技术面与估值面共振看多",
        "supporting_arguments": ["均线多头", "估值合理"],
        "acknowledged_risks": ["宏观波动"],
        "price_catalysts": ["业绩预告"]
    }"""
    result = parse_bull_argument(raw)
    assert isinstance(result, BullArgument)
    assert result.direction == "BULLISH"
    assert result.confidence == 0.75
    assert result.core_thesis == "技术面与估值面共振看多"
    assert len(result.supporting_arguments) == 2
    assert len(result.acknowledged_risks) == 1
    assert len(result.price_catalysts) == 1


def test_parse_valid_json_in_markdown_code_block():
    """Markdown 代码块包裹的 JSON 可正确剥离并解析。"""
    raw = """```json
{"direction": "BULLISH", "confidence": 0.6, "core_thesis": "x", "supporting_arguments": [], "acknowledged_risks": [], "price_catalysts": []}
```"""
    result = parse_bull_argument(raw)
    assert result.direction == "BULLISH"
    assert result.confidence == 0.6


def test_parse_invalid_json_raises_llm_output_parse_error():
    """非 JSON 时抛出 LLMOutputParseError。"""
    with pytest.raises(LLMOutputParseError) as exc_info:
        parse_bull_argument("not json at all")
    assert exc_info.value.code == "LLM_OUTPUT_PARSE_ERROR"


def test_parse_empty_string_raises():
    """空字符串时抛出 LLMOutputParseError。"""
    with pytest.raises(LLMOutputParseError):
        parse_bull_argument("")
