"""judge_node 与编排图测试：辩论成功后裁决写入 verdict、debate 为空跳过裁决、Gateway 异常降级、完整流水线、skip_debate、辩论失败时 verdict 为 null。"""
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.modules.coordinator.domain.dtos.research_dtos import ResearchRequest
from src.modules.coordinator.domain.model.enums import ExpertType
from src.modules.coordinator.domain.ports.research_expert_gateway import IResearchExpertGateway
from src.modules.coordinator.domain.ports.debate_gateway import IDebateGateway
from src.modules.coordinator.domain.ports.judge_gateway import IJudgeGateway
from src.modules.coordinator.infrastructure.orchestration.langgraph_orchestrator import (
    LangGraphResearchOrchestrator,
)


@pytest.fixture
def mock_research_gateway():
    """所有专家返回成功。"""
    g = AsyncMock(spec=IResearchExpertGateway)
    g.run_expert = AsyncMock(return_value={"signal": "NEUTRAL", "confidence": 0.8})
    return g


@pytest.fixture
def mock_debate_gateway():
    """辩论返回固定 dict（含裁决所需字段）。"""
    g = AsyncMock(spec=IDebateGateway)
    g.run_debate = AsyncMock(
        return_value={
            "symbol": "000001.SZ",
            "direction": "BULLISH",
            "confidence": 0.6,
            "bull_case": {"core_thesis": "多"},
            "bear_case": {"core_thesis": "空"},
            "risk_matrix": [{"risk": "R"}],
            "key_disagreements": [],
            "conflict_resolution": "综合偏多",
        }
    )
    return g


@pytest.fixture
def mock_judge_gateway():
    """裁决返回固定 dict。"""
    g = AsyncMock(spec=IJudgeGateway)
    g.run_verdict = AsyncMock(
        return_value={
            "symbol": "000001.SZ",
            "action": "BUY",
            "position_percent": 0.3,
            "confidence": 0.72,
            "entry_strategy": "分批",
            "stop_loss": "-5%",
            "take_profit": "+15%",
            "time_horizon": "3-6月",
            "risk_warnings": ["流动性"],
            "reasoning": "综合偏多",
        }
    )
    return g


@pytest.fixture
def mock_judge_gateway_raises():
    """裁决 Gateway 抛异常。"""
    g = AsyncMock(spec=IJudgeGateway)
    g.run_verdict = AsyncMock(side_effect=RuntimeError("裁决失败"))
    return g


@pytest.mark.asyncio
async def test_orchestrator_with_judge_returns_verdict(
    mock_research_gateway, mock_debate_gateway, mock_judge_gateway
):
    """编排器带 debate_gateway + judge_gateway 时，正常流程返回含 verdict 的结果。"""
    orchestrator = LangGraphResearchOrchestrator(
        mock_research_gateway,
        debate_gateway=mock_debate_gateway,
        judge_gateway=mock_judge_gateway,
    )
    request = ResearchRequest(
        symbol="000001.SZ",
        experts=[ExpertType.TECHNICAL_ANALYST],
        options={},
        skip_debate=False,
    )
    result = await orchestrator.run(request)
    assert result.debate_outcome is not None
    assert result.verdict is not None
    assert result.verdict.get("action") == "BUY"
    assert result.verdict.get("position_percent") == 0.3
    mock_judge_gateway.run_verdict.assert_called_once()


@pytest.mark.asyncio
async def test_skip_debate_true_returns_debate_outcome_and_verdict_null(
    mock_research_gateway, mock_debate_gateway, mock_judge_gateway
):
    """skip_debate=True 时响应 debate_outcome 和 verdict 均为 None。"""
    orchestrator = LangGraphResearchOrchestrator(
        mock_research_gateway,
        debate_gateway=mock_debate_gateway,
        judge_gateway=mock_judge_gateway,
    )
    request = ResearchRequest(
        symbol="000001.SZ",
        experts=[ExpertType.TECHNICAL_ANALYST],
        options={},
        skip_debate=True,
    )
    result = await orchestrator.run(request)
    assert result.debate_outcome is None
    assert result.verdict is None
    mock_debate_gateway.run_debate.assert_not_called()
    mock_judge_gateway.run_verdict.assert_not_called()


@pytest.mark.asyncio
async def test_debate_failure_verdict_null_overall_status_unchanged(
    mock_research_gateway, mock_judge_gateway
):
    """辩论异常后 debate_outcome 为 None、verdict 为 None，overall_status 不受影响（研究仍成功）。"""
    debate_gw = AsyncMock(spec=IDebateGateway)
    debate_gw.run_debate = AsyncMock(side_effect=RuntimeError("辩论失败"))
    orchestrator = LangGraphResearchOrchestrator(
        mock_research_gateway,
        debate_gateway=debate_gw,
        judge_gateway=mock_judge_gateway,
    )
    request = ResearchRequest(
        symbol="000001.SZ",
        experts=[ExpertType.TECHNICAL_ANALYST],
        options={},
        skip_debate=False,
    )
    result = await orchestrator.run(request)
    assert result.overall_status == "completed"
    assert result.debate_outcome is None
    assert result.verdict is None
    mock_judge_gateway.run_verdict.assert_not_called()


@pytest.mark.asyncio
async def test_judge_gateway_exception_downgrade_verdict_null(
    mock_research_gateway, mock_debate_gateway, mock_judge_gateway_raises
):
    """辩论成功但裁决异常时 verdict 为 None，debate_outcome 正常返回，overall_status 不受影响。"""
    orchestrator = LangGraphResearchOrchestrator(
        mock_research_gateway,
        debate_gateway=mock_debate_gateway,
        judge_gateway=mock_judge_gateway_raises,
    )
    request = ResearchRequest(
        symbol="000001.SZ",
        experts=[ExpertType.TECHNICAL_ANALYST],
        options={},
        skip_debate=False,
    )
    result = await orchestrator.run(request)
    assert result.overall_status == "completed"
    assert result.debate_outcome is not None
    assert result.verdict is None
