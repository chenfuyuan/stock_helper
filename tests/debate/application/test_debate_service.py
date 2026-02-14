"""DebateService 单元测试：三阶段正常流程返回完整 DebateOutcomeDTO；某 Agent 抛异常时向上传播。"""

from unittest.mock import AsyncMock

import pytest

from src.modules.debate.application.services.debate_service import (
    DebateService,
)
from src.modules.debate.domain.dtos.bull_bear_argument import (
    BearArgument,
    BullArgument,
)
from src.modules.debate.domain.dtos.debate_input import (
    DebateInput,
    ExpertSummary,
)
from src.modules.debate.domain.dtos.resolution_result import ResolutionResult
from src.modules.debate.domain.dtos.risk_matrix import RiskItemDTO


def _sample_debate_input() -> DebateInput:
    return DebateInput(
        symbol="000001.SZ",
        expert_summaries={
            "technical_analyst": ExpertSummary(
                signal="BULLISH",
                confidence=0.8,
                reasoning="技术面偏多",
                risk_warning="跌破支撑则失效",
            ),
        },
    )


@pytest.fixture
def mock_bull_agent():
    a = AsyncMock()
    a.advocate = AsyncMock(
        return_value=BullArgument(
            direction="BULLISH",
            confidence=0.75,
            core_thesis="多头论点",
            supporting_arguments=["a", "b"],
            acknowledged_risks=["r"],
            price_catalysts=["c"],
        )
    )
    return a


@pytest.fixture
def mock_bear_agent():
    a = AsyncMock()
    a.advocate = AsyncMock(
        return_value=BearArgument(
            direction="BEARISH",
            confidence=0.7,
            core_thesis="空头论点",
            supporting_arguments=["x"],
            acknowledged_strengths=["s"],
            risk_triggers=["t"],
        )
    )
    return a


@pytest.fixture
def mock_resolution_agent():
    a = AsyncMock()
    a.resolve = AsyncMock(
        return_value=ResolutionResult(
            direction="NEUTRAL",
            confidence=0.55,
            bull_case_summary="多头摘要",
            bear_case_summary="空头摘要",
            risk_matrix=[
                RiskItemDTO(
                    risk="政策风险",
                    probability="中",
                    impact="高",
                    mitigation="分散",
                )
            ],
            key_disagreements=["估值分歧"],
            conflict_resolution="综合裁决为中性",
        )
    )
    return a


@pytest.mark.asyncio
async def test_run_returns_complete_debate_outcome_dto(
    mock_bull_agent, mock_bear_agent, mock_resolution_agent
):
    """三阶段正常完成时返回包含 direction、confidence、risk_matrix 等的 DebateOutcomeDTO。"""
    service = DebateService(
        bull_agent=mock_bull_agent,
        bear_agent=mock_bear_agent,
        resolution_agent=mock_resolution_agent,
    )
    outcome = await service.run(_sample_debate_input())
    assert outcome.symbol == "000001.SZ"
    assert outcome.direction == "NEUTRAL"
    assert outcome.confidence == 0.55
    assert outcome.bull_case.core_thesis == "多头论点"
    assert outcome.bear_case.core_thesis == "空头论点"
    assert len(outcome.risk_matrix) == 1
    assert outcome.risk_matrix[0].risk == "政策风险"
    assert outcome.key_disagreements == ["估值分歧"]
    assert outcome.conflict_resolution == "综合裁决为中性"


@pytest.mark.asyncio
async def test_bull_agent_failure_propagates(
    mock_bear_agent, mock_resolution_agent
):
    """Bull Agent 抛异常时 DebateService 将异常向上传播。"""
    bull = AsyncMock()
    bull.advocate = AsyncMock(side_effect=RuntimeError("Bull 执行失败"))
    service = DebateService(
        bull_agent=bull,
        bear_agent=mock_bear_agent,
        resolution_agent=mock_resolution_agent,
    )
    with pytest.raises(RuntimeError, match="Bull 执行失败"):
        await service.run(_sample_debate_input())


@pytest.mark.asyncio
async def test_bear_agent_failure_propagates(
    mock_bull_agent, mock_resolution_agent
):
    """Bear Agent 抛异常时 DebateService 将异常向上传播。"""
    bear = AsyncMock()
    bear.advocate = AsyncMock(side_effect=ValueError("Bear 执行失败"))
    service = DebateService(
        bull_agent=mock_bull_agent,
        bear_agent=bear,
        resolution_agent=mock_resolution_agent,
    )
    with pytest.raises(ValueError, match="Bear 执行失败"):
        await service.run(_sample_debate_input())


@pytest.mark.asyncio
async def test_resolution_agent_failure_propagates(
    mock_bull_agent, mock_bear_agent
):
    """Resolution Agent 抛异常时 DebateService 将异常向上传播。"""
    resolution = AsyncMock()
    resolution.resolve = AsyncMock(side_effect=RuntimeError("Resolution 失败"))
    service = DebateService(
        bull_agent=mock_bull_agent,
        bear_agent=mock_bear_agent,
        resolution_agent=resolution,
    )
    with pytest.raises(RuntimeError, match="Resolution 失败"):
        await service.run(_sample_debate_input())
