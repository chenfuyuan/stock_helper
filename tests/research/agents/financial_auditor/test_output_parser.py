"""
Task 4.3：财务审计员输出解析测试。
合法 JSON 解析后字段正确；非 JSON 或缺字段时解析失败且不返回未校验字符串；
score/signal 不匹配时自动以 score 为准修正 signal。
"""

import pytest

from src.modules.research.domain.dtos.financial_dtos import (
    FinancialAuditResultDTO,
)
from src.modules.research.domain.exceptions import LLMOutputParseError
from src.modules.research.infrastructure.agents.financial_auditor.output_parser import (  # noqa: E501
    parse_financial_audit_result,
)


def _make_valid_json(
    financial_score: int = 75,
    signal: str = "BULLISH",
    confidence: float = 0.8,
) -> str:
    return f"""{{
        "financial_score": {financial_score},
        "signal": "{signal}",
        "confidence": {confidence},
        "summary_reasoning": "ROIC 达 18%",
        "dimension_analyses": [
            {{
                "dimension": "盈利含金量",
                "score": 80,
                "assessment": "好",
                "key_findings": []
            }},
            {{
                "dimension": "运营效率",
                "score": 70,
                "assessment": "中",
                "key_findings": []
            }},
            {{
                "dimension": "资本回报",
                "score": 75,
                "assessment": "好",
                "key_findings": []
            }},
            {{
                "dimension": "偿债能力",
                "score": 72,
                "assessment": "中",
                "key_findings": []
            }},
            {{
                "dimension": "成长加速度",
                "score": 78,
                "assessment": "好",
                "key_findings": []
            }}
        ],
        "key_risks": [],
        "risk_warning": ""
    }}"""


def test_parse_valid_json_returns_dto_with_correct_fields():
    """合法 JSON 解析后字段正确，
    financial_score、signal、confidence、
    dimension_analyses 符合契约。
    """
    raw = _make_valid_json()
    result = parse_financial_audit_result(raw)
    assert isinstance(result, FinancialAuditResultDTO)
    assert result.financial_score == 75
    assert result.signal == "BULLISH"
    assert result.confidence == 0.8
    assert len(result.dimension_analyses) == 5


def test_parse_valid_json_stripped_from_markdown_code_block():
    """Markdown 代码块包裹的 JSON 可正确剥离并解析。"""
    raw = f"""```json
{_make_valid_json(signal="NEUTRAL", financial_score=55)}
```"""
    result = parse_financial_audit_result(raw)
    assert result.signal == "NEUTRAL"
    assert result.financial_score == 55


def test_parse_invalid_json_raises():
    """非 JSON 时解析失败并抛出 LLMOutputParseError。"""
    with pytest.raises(LLMOutputParseError) as exc_info:
        parse_financial_audit_result("not json at all")
    assert "JSON" in exc_info.value.message or "解析" in exc_info.value.message
    assert exc_info.value.code == "LLM_OUTPUT_PARSE_ERROR"


def test_parse_missing_required_field_raises():
    """缺少必填字段时解析失败。"""
    raw = '{"financial_score": 75, "signal": "BULLISH", "confidence": 0.8}'
    with pytest.raises(LLMOutputParseError):
        parse_financial_audit_result(raw)


def test_parse_score_signal_mismatch_auto_corrects():
    """score 与 signal 不匹配时，以 score 为准自动修正 signal。"""
    # score=75 应映射为 BULLISH，但 LLM 返回了 NEUTRAL
    raw = _make_valid_json(financial_score=75, signal="NEUTRAL")
    result = parse_financial_audit_result(raw)
    assert result.financial_score == 75
    assert result.signal == "BULLISH"


def test_parse_empty_string_raises():
    """空字符串时抛出明确错误。"""
    with pytest.raises(LLMOutputParseError):
        parse_financial_audit_result("")
