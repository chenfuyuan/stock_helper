"""DebateGatewayAdapter 单元测试：per-expert 字段映射、调试字段过滤、仅成功专家被包含。"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.modules.coordinator.infrastructure.adapters.debate_gateway_adapter import (
    DebateGatewayAdapter,
)
from src.modules.debate.application.dtos.debate_outcome_dto import (
    BearCaseDTO,
    BullCaseDTO,
    DebateOutcomeDTO,
)
from src.modules.debate.domain.dtos.risk_matrix import RiskItemDTO


class _MockAsyncSessionContext:
    async def __aenter__(self):
        return MagicMock()

    async def __aexit__(self, *args):
        pass


def _mock_session_factory():
    return _MockAsyncSessionContext()


@pytest.fixture
def mock_debate_container():
    """Mock DebateContainer：debate_service().run() 返回固定 DebateOutcomeDTO。"""
    outcome = DebateOutcomeDTO(
        symbol="000001.SZ",
        direction="NEUTRAL",
        confidence=0.6,
        bull_case=BullCaseDTO(core_thesis="b", supporting_arguments=[], acknowledged_risks=[]),
        bear_case=BearCaseDTO(core_thesis="e", supporting_arguments=[], acknowledged_strengths=[]),
        risk_matrix=[RiskItemDTO(risk="R", probability="中", impact="高", mitigation="")],
        key_disagreements=[],
        conflict_resolution="ok",
    )
    container = MagicMock()
    svc = MagicMock()
    svc.run = AsyncMock(return_value=outcome)
    container.debate_service.return_value = svc
    return container


@pytest.mark.asyncio
async def test_technical_analyst_field_mapping(mock_debate_container):
    """technical_analyst 结果映射为 ExpertSummary（signal/confidence/summary_reasoning/risk_warning），不含 input/output/indicators。"""  # noqa: E501
    with patch(
        "src.modules.coordinator.infrastructure.adapters.debate_gateway_adapter.DebateContainer",
        return_value=mock_debate_container,
    ):
        adapter = DebateGatewayAdapter(_mock_session_factory())
        result = await adapter.run_debate(
            symbol="000001.SZ",
            expert_results={
                "technical_analyst": {
                    "signal": "BULLISH",
                    "confidence": 0.78,
                    "summary_reasoning": "技术面偏多",
                    "risk_warning": "跌破支撑失效",
                    "input": "user prompt raw",
                    "output": "llm raw",
                    "technical_indicators": {"ma5": 10},
                },
            },
        )
    assert result["symbol"] == "000001.SZ"
    assert result["direction"] == "NEUTRAL"
    # 内部转换仅取 signal/confidence/reasoning/risk_warning，不传 input/output/indicators 给 Debate
    mock_debate_container.debate_service().run.assert_called_once()
    call_args = mock_debate_container.debate_service().run.call_args[0][0]
    assert call_args.symbol == "000001.SZ"
    assert "technical_analyst" in call_args.expert_summaries
    s = call_args.expert_summaries["technical_analyst"]
    assert s.signal == "BULLISH"
    assert s.confidence == 0.78
    assert s.reasoning == "技术面偏多"
    assert s.risk_warning == "跌破支撑失效"


@pytest.mark.asyncio
async def test_valuation_modeler_field_normalization(mock_debate_container):
    """valuation_modeler 使用 valuation_verdict/confidence_score/reasoning_summary/risk_factors 归一化。"""  # noqa: E501
    with patch(
        "src.modules.coordinator.infrastructure.adapters.debate_gateway_adapter.DebateContainer",
        return_value=mock_debate_container,
    ):
        adapter = DebateGatewayAdapter(_mock_session_factory())
        await adapter.run_debate(
            symbol="000001.SZ",
            expert_results={
                "valuation_modeler": {
                    "valuation_verdict": "BEARISH",
                    "confidence_score": 0.65,
                    "reasoning_summary": "估值偏高",
                    "risk_factors": ["流动性", "政策"],
                },
            },
        )
    call_args = mock_debate_container.debate_service().run.call_args[0][0]
    s = call_args.expert_summaries["valuation_modeler"]
    assert s.signal == "BEARISH"
    assert s.confidence == 0.65
    assert s.reasoning == "估值偏高"
    assert "流动性" in s.risk_warning and "政策" in s.risk_warning


@pytest.mark.asyncio
async def test_catalyst_detective_nested_result(mock_debate_container):
    """catalyst_detective 从 result 内取 catalyst_assessment/confidence_score/catalyst_summary/negative_catalysts。"""  # noqa: E501
    with patch(
        "src.modules.coordinator.infrastructure.adapters.debate_gateway_adapter.DebateContainer",
        return_value=mock_debate_container,
    ):
        adapter = DebateGatewayAdapter(_mock_session_factory())
        await adapter.run_debate(
            symbol="000001.SZ",
            expert_results={
                "catalyst_detective": {
                    "result": {
                        "catalyst_assessment": "NEUTRAL",
                        "confidence_score": 0.7,
                        "catalyst_summary": "催化剂摘要",
                        "negative_catalysts": ["利空1", "利空2"],
                    },
                },
            },
        )
    call_args = mock_debate_container.debate_service().run.call_args[0][0]
    s = call_args.expert_summaries["catalyst_detective"]
    assert s.signal == "NEUTRAL"
    assert s.confidence == 0.7
    assert s.reasoning == "催化剂摘要"
    assert "利空1" in s.risk_warning


@pytest.mark.asyncio
async def test_only_successful_experts_included(mock_debate_container):
    """仅成功专家被包含；无法映射的条目不加入 expert_summaries。"""
    with patch(
        "src.modules.coordinator.infrastructure.adapters.debate_gateway_adapter.DebateContainer",
        return_value=mock_debate_container,
    ):
        adapter = DebateGatewayAdapter(_mock_session_factory())
        await adapter.run_debate(
            symbol="000001.SZ",
            expert_results={
                "technical_analyst": {
                    "signal": "BULLISH",
                    "confidence": 0.8,
                    "summary_reasoning": "x",
                    "risk_warning": "",
                },
                "unknown_expert": {"foo": "bar"},
            },
        )
    call_args = mock_debate_container.debate_service().run.call_args[0][0]
    assert "technical_analyst" in call_args.expert_summaries
    assert "unknown_expert" not in call_args.expert_summaries


@pytest.mark.asyncio
async def test_return_value_is_dict_serialization(mock_debate_container):
    """run_debate 返回 DebateOutcomeDTO 的 dict（.model_dump()）。"""
    with patch(
        "src.modules.coordinator.infrastructure.adapters.debate_gateway_adapter.DebateContainer",
        return_value=mock_debate_container,
    ):
        adapter = DebateGatewayAdapter(_mock_session_factory())
        result = await adapter.run_debate(
            symbol="000001.SZ",
            expert_results={
                "technical_analyst": {
                    "signal": "BULLISH",
                    "confidence": 0.8,
                    "summary_reasoning": "",
                    "risk_warning": "",
                }
            },
        )
    assert isinstance(result, dict)
    assert result["symbol"] == "000001.SZ"
    assert "direction" in result
    assert "risk_matrix" in result
