"""
Task 2.4：FinancialAuditResultDTO 校验的测试。
financial_score ∈ [0, 100]；signal 为五值之一；confidence ∈ [0, 1]；dimension_analyses 含 5 个维度。
"""
import pytest
from pydantic import ValidationError

from src.modules.research.domain.financial_dtos import (
    FinancialAuditResultDTO,
    DimensionAnalysisDTO,
)


def _make_dimension(name: str) -> DimensionAnalysisDTO:
    return DimensionAnalysisDTO(
        dimension=name,
        score=70.0,
        assessment="测试",
        key_findings=[],
    )


def _make_valid_result(
    financial_score: int = 75,
    signal: str = "BULLISH",
    confidence: float = 0.8,
) -> FinancialAuditResultDTO:
    return FinancialAuditResultDTO(
        financial_score=financial_score,
        signal=signal,
        confidence=confidence,
        summary_reasoning="测试审计逻辑",
        dimension_analyses=[
            _make_dimension("盈利含金量"),
            _make_dimension("运营效率与造假侦测"),
            _make_dimension("资本回报与护城河"),
            _make_dimension("偿债与生存能力"),
            _make_dimension("成长加速度"),
        ],
        key_risks=[],
        risk_warning="",
    )


def test_result_dto_signal_only_allow_five_values():
    """signal 仅允许五值之一。"""
    for sig in ("STRONG_BULLISH", "BULLISH", "NEUTRAL", "BEARISH", "STRONG_BEARISH"):
        r = _make_valid_result(signal=sig)
        assert r.signal == sig

    with pytest.raises(ValidationError):
        FinancialAuditResultDTO(
            financial_score=75,
            signal="INVALID",
            confidence=0.8,
            summary_reasoning="",
            dimension_analyses=[_make_dimension(f"d{i}") for i in range(5)],
            key_risks=[],
            risk_warning="",
        )


def test_result_dto_financial_score_in_range():
    """financial_score 必须在 [0, 100]。"""
    _make_valid_result(financial_score=0)
    _make_valid_result(financial_score=100)
    with pytest.raises(ValidationError):
        _make_valid_result(financial_score=-1)
    with pytest.raises(ValidationError):
        _make_valid_result(financial_score=101)


def test_result_dto_confidence_in_zero_one():
    """confidence 必须在 [0, 1]。"""
    _make_valid_result(confidence=0.0)
    _make_valid_result(confidence=1.0)
    with pytest.raises(ValidationError):
        _make_valid_result(confidence=1.5)


def test_result_dto_dimension_analyses_has_five_dimensions():
    """dimension_analyses 应包含 5 个维度。"""
    r = _make_valid_result()
    assert len(r.dimension_analyses) == 5
    for d in r.dimension_analyses:
        assert isinstance(d, DimensionAnalysisDTO)
        assert d.dimension
        assert 0 <= d.score <= 100
