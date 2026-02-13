"""debate_node 与 skip_debate 测试：正常写入 debate_outcome、全部失败跳过、Gateway 异常降级、skip_debate 时 debate_outcome 为 null。"""
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.modules.coordinator.domain.dtos.research_dtos import ResearchRequest
from src.modules.coordinator.domain.model.enums import ExpertType
from src.modules.coordinator.domain.ports.research_expert_gateway import IResearchExpertGateway
from src.modules.coordinator.domain.ports.debate_gateway import IDebateGateway
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
    """辩论返回固定 dict。"""
    g = AsyncMock(spec=IDebateGateway)
    g.run_debate = AsyncMock(
        return_value={"direction": "NEUTRAL", "confidence": 0.6, "symbol": "000001.SZ"}
    )
    return g


@pytest.fixture
def mock_debate_gateway_raises():
    """辩论 Gateway 抛异常。"""
    g = AsyncMock(spec=IDebateGateway)
    g.run_debate = AsyncMock(side_effect=RuntimeError("辩论失败"))
    return g


@pytest.mark.asyncio
async def test_orchestrator_with_debate_returns_debate_outcome(
    mock_research_gateway, mock_debate_gateway
):
    """编排器带 debate_gateway 时，正常流程返回含 debate_outcome 的结果。"""
    orchestrator = LangGraphResearchOrchestrator(
        mock_research_gateway,
        debate_gateway=mock_debate_gateway,
    )
    request = ResearchRequest(
        symbol="000001.SZ",
        experts=[ExpertType.TECHNICAL_ANALYST],
        options={},
        skip_debate=False,
    )
    result = await orchestrator.run(request)
    assert result.debate_outcome is not None
    assert result.debate_outcome.get("direction") == "NEUTRAL"
    assert result.debate_outcome.get("symbol") == "000001.SZ"


@pytest.mark.asyncio
async def test_skip_debate_true_returns_debate_outcome_null(
    mock_research_gateway, mock_debate_gateway
):
    """skip_debate=True 时编排不调用 debate_gateway，result.debate_outcome 为 None。"""
    orchestrator = LangGraphResearchOrchestrator(
        mock_research_gateway,
        debate_gateway=mock_debate_gateway,
    )
    request = ResearchRequest(
        symbol="000001.SZ",
        experts=[ExpertType.TECHNICAL_ANALYST],
        options={},
        skip_debate=True,
    )
    result = await orchestrator.run(request)
    assert result.debate_outcome is None
    mock_debate_gateway.run_debate.assert_not_called()


@pytest.mark.asyncio
async def test_all_experts_fail_debate_skipped():
    """全部专家失败时 debate_node 跳过辩论，debate_outcome 为空 dict 转 None。"""
    gateway = AsyncMock(spec=IResearchExpertGateway)
    gateway.run_expert = AsyncMock(side_effect=RuntimeError("专家失败"))
    debate_gw = AsyncMock(spec=IDebateGateway)
    orchestrator = LangGraphResearchOrchestrator(gateway, debate_gateway=debate_gw)
    request = ResearchRequest(
        symbol="000001.SZ",
        experts=[ExpertType.TECHNICAL_ANALYST],
        options={},
        skip_debate=False,
    )
    result = await orchestrator.run(request)
    # overall_status 为 failed，debate_node 不调用 run_debate，debate_outcome 为 {}
    assert result.overall_status == "failed"
    assert result.debate_outcome is None  # 空 dict 在 orchestrator 中转为 None
    debate_gw.run_debate.assert_not_called()


@pytest.mark.asyncio
async def test_debate_gateway_exception_downgrade(
    mock_research_gateway, mock_debate_gateway_raises
):
    """辩论 Gateway 抛异常时 debate_node 降级，debate_outcome 为空（None），overall_status 不受影响。"""
    orchestrator = LangGraphResearchOrchestrator(
        mock_research_gateway,
        debate_gateway=mock_debate_gateway_raises,
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
