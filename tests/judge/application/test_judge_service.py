"""JudgeService 单元测试：Mock IJudgeVerdictAgentPort，验证正常流程返回完整 VerdictDTO（含 symbol 注入）；异常向上传播。"""

from unittest.mock import AsyncMock

import pytest

from src.modules.judge.application.services.judge_service import JudgeService
from src.modules.judge.domain.dtos.judge_input import JudgeInput
from src.modules.judge.domain.dtos.verdict_result import VerdictResult


def _sample_judge_input() -> JudgeInput:
    return JudgeInput(
        symbol="000001.SZ",
        direction="BULLISH",
        confidence=0.7,
        bull_thesis="估值偏低",
        bear_thesis="景气度下行",
        risk_factors=["政策", "流动性"],
        key_disagreements=["估值分歧"],
        conflict_resolution="综合偏多",
    )


@pytest.fixture
def mock_verdict_agent():
    """Mock IJudgeVerdictAgentPort 返回固定 VerdictResult。"""
    a = AsyncMock()
    a.judge = AsyncMock(
        return_value=VerdictResult(
            action="BUY",
            position_percent=0.3,
            confidence=0.72,
            entry_strategy="分批建仓",
            stop_loss="-5%",
            take_profit="+15%",
            time_horizon="3-6个月",
            risk_warnings=["流动性风险"],
            reasoning="综合辩论偏多",
        )
    )
    return a


@pytest.mark.asyncio
async def test_run_returns_complete_verdict_dto_with_symbol_injected(
    mock_verdict_agent,
):
    """正常流程返回完整 VerdictDTO，symbol 从 JudgeInput 注入。"""
    service = JudgeService(verdict_agent=mock_verdict_agent)
    result = await service.run(_sample_judge_input())
    assert result.symbol == "000001.SZ"
    assert result.action == "BUY"
    assert result.position_percent == 0.3
    assert result.confidence == 0.72
    assert result.entry_strategy == "分批建仓"
    assert result.stop_loss == "-5%"
    assert result.take_profit == "+15%"
    assert result.time_horizon == "3-6个月"
    assert result.risk_warnings == ["流动性风险"]
    assert result.reasoning == "综合辩论偏多"


@pytest.mark.asyncio
async def test_agent_exception_propagates():
    """Agent Port 抛异常时 JudgeService 将异常向上传播。"""
    agent = AsyncMock()
    agent.judge = AsyncMock(side_effect=RuntimeError("裁决失败"))
    service = JudgeService(verdict_agent=agent)
    with pytest.raises(RuntimeError, match="裁决失败"):
        await service.run(_sample_judge_input())
