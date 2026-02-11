"""
Task 2.1 Red：TechnicalAnalysisResultDTO 校验的测试。
signal 仅允许 BULLISH/BEARISH/NEUTRAL；confidence 在 [0,1]；必填字段缺失时校验失败。
"""
import pytest
from pydantic import ValidationError

from src.modules.research.domain.dtos import TechnicalAnalysisResultDTO, KeyTechnicalLevelsDTO


def test_result_dto_signal_only_allow_bullish_bearish_neutral():
    """signal 仅允许三值之一。"""
    valid = TechnicalAnalysisResultDTO(
        signal="BULLISH",
        confidence=0.8,
        summary_reasoning="测试",
        key_technical_levels=KeyTechnicalLevelsDTO(support=10.0, resistance=11.0),
        risk_warning="跌破10",
    )
    assert valid.signal == "BULLISH"

    with pytest.raises(ValidationError):
        TechnicalAnalysisResultDTO(
            signal="INVALID",
            confidence=0.8,
            summary_reasoning="测试",
            key_technical_levels=KeyTechnicalLevelsDTO(support=10.0, resistance=11.0),
            risk_warning="",
        )


def test_result_dto_confidence_in_zero_one():
    """confidence 必须在 [0, 1]。"""
    TechnicalAnalysisResultDTO(
        signal="NEUTRAL",
        confidence=0.0,
        summary_reasoning="",
        key_technical_levels=KeyTechnicalLevelsDTO(support=0.0, resistance=0.0),
        risk_warning="",
    )
    TechnicalAnalysisResultDTO(
        signal="NEUTRAL",
        confidence=1.0,
        summary_reasoning="",
        key_technical_levels=KeyTechnicalLevelsDTO(support=0.0, resistance=0.0),
        risk_warning="",
    )
    with pytest.raises(ValidationError):
        TechnicalAnalysisResultDTO(
            signal="NEUTRAL",
            confidence=1.5,
            summary_reasoning="",
            key_technical_levels=KeyTechnicalLevelsDTO(support=0.0, resistance=0.0),
            risk_warning="",
        )


def test_result_dto_missing_required_fails():
    """必填字段缺失时校验失败。"""
    with pytest.raises(ValidationError):
        TechnicalAnalysisResultDTO(
            signal="BULLISH",
            # missing confidence, summary_reasoning, key_technical_levels, risk_warning
        )
