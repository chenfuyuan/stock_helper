import pytest

from src.modules.research.domain.exceptions import LLMOutputParseError
from src.modules.research.infrastructure.agents.catalyst_detective.output_parser import (
    parse_catalyst_detective_result,
)


def test_parse_valid_json():
    # Valid JSON string
    raw = """
    ```json
    {
        "catalyst_assessment": "Positive (正面催化)",
        "confidence_score": 0.85,
        "catalyst_summary": "Summary...",
        "dimension_analyses": [],
        "positive_catalysts": [],
        "negative_catalysts": [],
        "information_sources": ["http://test.com"]
    }
    ```
    """
    dto = parse_catalyst_detective_result(raw)
    assert dto.catalyst_assessment == "Positive (正面催化)"
    assert dto.confidence_score == 0.85


def test_parse_with_thinking_tags():
    raw = """
    <think>
    Thinking process...
    </think>
    {
        "catalyst_assessment": "Neutral (中性)",
        "confidence_score": 0.5,
        "catalyst_summary": "S",
        "dimension_analyses": [],
        "positive_catalysts": [],
        "negative_catalysts": [],
        "information_sources": []
    }
    """
    dto = parse_catalyst_detective_result(raw)
    assert dto.catalyst_assessment == "Neutral (中性)"


def test_parse_invalid_json():
    raw = "Not JSON"
    with pytest.raises(LLMOutputParseError) as exc:
        parse_catalyst_detective_result(raw)
    assert "不是合法 JSON" in str(exc.value)


def test_parse_missing_fields():
    raw = "{}"  # Valid JSON but missing fields
    with pytest.raises(LLMOutputParseError) as exc:
        parse_catalyst_detective_result(raw)
    assert "不符合契约" in str(exc.value)
