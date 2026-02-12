"""
任务 10.3：估值建模师输出解析测试。
合法 JSON 解析后字段正确；非 JSON 或缺字段时解析失败且不返回未校验字符串；
含 `<think>` 标签时正确剥离后解析。
"""
import pytest

from src.modules.research.infrastructure.agents.valuation_modeler.output_parser import (
    parse_valuation_result,
)
from src.modules.research.domain.dtos.valuation_dtos import ValuationResultDTO
from src.modules.research.domain.exceptions import LLMOutputParseError


def _make_valid_json(
    valuation_verdict: str = "Undervalued (低估)",
    confidence_score: float = 0.85,
) -> str:
    return f'''{{
        "valuation_verdict": "{valuation_verdict}",
        "confidence_score": {confidence_score},
        "estimated_intrinsic_value_range": {{
            "lower_bound": "基于 Graham 模型推导的 18.5 元",
            "upper_bound": "基于历史均值 PE 推导的 25.0 元"
        }},
        "key_evidence": [
            "PE 处于历史 5% 分位，极度悲观",
            "PEG 仅为 0.8，且 ROE 高达 20%"
        ],
        "risk_factors": [
            "毛利率同比下滑 2%",
            "资产负债率 65%"
        ],
        "reasoning_summary": "综合三模型显示低估，但需关注盈利质量下滑风险。"
    }}'''


def test_parse_valid_json_returns_dto_with_correct_fields():
    """合法 JSON 解析后字段正确，valuation_verdict、confidence_score、key_evidence 等符合契约。"""
    raw = _make_valid_json()
    result = parse_valuation_result(raw)
    assert isinstance(result, ValuationResultDTO)
    assert result.valuation_verdict == "Undervalued (低估)"
    assert result.confidence_score == 0.85
    assert len(result.key_evidence) >= 1
    assert len(result.risk_factors) >= 1
    assert result.estimated_intrinsic_value_range.lower_bound == "基于 Graham 模型推导的 18.5 元"


def test_parse_valid_json_stripped_from_markdown_code_block():
    """Markdown 代码块包裹的 JSON 可正确剥离并解析。"""
    raw = f"""```json
{_make_valid_json(valuation_verdict="Fair (合理)", confidence_score=0.6)}
```"""
    result = parse_valuation_result(raw)
    assert result.valuation_verdict == "Fair (合理)"
    assert result.confidence_score == 0.6


def test_parse_with_thinking_tags_strips_before_parsing():
    """含 `<think>` 标签时正确剥离后解析。"""
    raw = f"""<think>
这是推理过程，应该被剥离...
计算 PEG = 0.8...
</think>
{_make_valid_json()}"""
    result = parse_valuation_result(raw)
    assert isinstance(result, ValuationResultDTO)
    assert result.valuation_verdict == "Undervalued (低估)"


def test_parse_invalid_json_raises():
    """非 JSON 时解析失败并抛出 LLMOutputParseError。"""
    with pytest.raises(LLMOutputParseError) as exc_info:
        parse_valuation_result("not json at all")
    assert "JSON" in exc_info.value.message or "解析" in exc_info.value.message
    assert exc_info.value.code == "LLM_OUTPUT_PARSE_ERROR"


def test_parse_missing_required_field_raises():
    """缺少必填字段时解析失败。"""
    raw = '{"valuation_verdict": "Undervalued (低估)", "confidence_score": 0.8}'
    with pytest.raises(LLMOutputParseError):
        parse_valuation_result(raw)


def test_parse_invalid_verdict_value_raises():
    """valuation_verdict 不为三值之一时解析失败。"""
    raw = '''{"valuation_verdict": "INVALID", "confidence_score": 0.8, 
    "estimated_intrinsic_value_range": {"lower_bound": "18", "upper_bound": "25"},
    "key_evidence": ["test"], "risk_factors": ["test"], "reasoning_summary": "test"}'''
    with pytest.raises(LLMOutputParseError):
        parse_valuation_result(raw)


def test_parse_confidence_out_of_range_raises():
    """confidence_score 超出 [0, 1] 范围时解析失败。"""
    raw = _make_valid_json(confidence_score=1.5)
    with pytest.raises(LLMOutputParseError):
        parse_valuation_result(raw)


def test_parse_empty_key_evidence_raises():
    """key_evidence 为空列表时解析失败（要求非空）。"""
    raw = '''{"valuation_verdict": "Fair (合理)", "confidence_score": 0.7,
    "estimated_intrinsic_value_range": {"lower_bound": "20", "upper_bound": "25"},
    "key_evidence": [], "risk_factors": ["test"], "reasoning_summary": "test"}'''
    with pytest.raises(LLMOutputParseError):
        parse_valuation_result(raw)


def test_parse_empty_string_raises():
    """空字符串时抛出明确错误。"""
    with pytest.raises(LLMOutputParseError):
        parse_valuation_result("")
