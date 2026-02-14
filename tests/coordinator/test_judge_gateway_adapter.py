"""JudgeGatewayAdapter 单元测试：debate_outcome → JudgeInput 字段映射、risk_factors 提取、细节字段过滤。"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.modules.coordinator.infrastructure.adapters.judge_gateway_adapter import (
    JudgeGatewayAdapter,
)
from src.modules.judge.application.dtos.verdict_dto import VerdictDTO


def _mock_session_factory():
    class _Ctx:
        async def __aenter__(self):
            return MagicMock()

        async def __aexit__(self, *args):
            pass

    return _Ctx()


@pytest.fixture
def mock_judge_container():
    """Mock JudgeContainer：judge_service().run() 返回固定 VerdictDTO。"""
    verdict = VerdictDTO(
        symbol="000001.SZ",
        action="BUY",
        position_percent=0.3,
        confidence=0.72,
        entry_strategy="分批建仓",
        stop_loss="-5%",
        take_profit="+15%",
        time_horizon="3-6个月",
        risk_warnings=["流动性风险"],
        reasoning="综合偏多",
    )
    container = MagicMock()
    svc = MagicMock()
    svc.run = AsyncMock(return_value=verdict)
    container.judge_service.return_value = svc
    return container


@pytest.mark.asyncio
async def test_bull_thesis_and_bear_thesis_extraction(mock_judge_container):
    """debate_outcome 中 bull_case.core_thesis、bear_case.core_thesis 正确映射到 JudgeInput。"""
    with patch(
        "src.modules.coordinator.infrastructure.adapters.judge_gateway_adapter.JudgeContainer",
        return_value=mock_judge_container,
    ):
        adapter = JudgeGatewayAdapter(_mock_session_factory())
        await adapter.run_verdict(
            symbol="000001.SZ",
            debate_outcome={
                "direction": "BULLISH",
                "confidence": 0.7,
                "bull_case": {"core_thesis": "估值低于内在价值"},
                "bear_case": {"core_thesis": "行业景气度下行"},
                "risk_matrix": [],
                "key_disagreements": [],
                "conflict_resolution": "综合偏多",
            },
        )
    call_args = mock_judge_container.judge_service().run.call_args[0][0]
    assert call_args.bull_thesis == "估值低于内在价值"
    assert call_args.bear_thesis == "行业景气度下行"


@pytest.mark.asyncio
async def test_risk_factors_from_risk_matrix(mock_judge_container):
    """risk_matrix 仅提取 risk 字段为 list[str]，不包含 probability/impact/mitigation。"""
    with patch(
        "src.modules.coordinator.infrastructure.adapters.judge_gateway_adapter.JudgeContainer",
        return_value=mock_judge_container,
    ):
        adapter = JudgeGatewayAdapter(_mock_session_factory())
        await adapter.run_verdict(
            symbol="000001.SZ",
            debate_outcome={
                "direction": "BULLISH",
                "confidence": 0.7,
                "bull_case": {"core_thesis": "a"},
                "bear_case": {"core_thesis": "b"},
                "risk_matrix": [
                    {
                        "risk": "政策风险",
                        "probability": "高",
                        "impact": "中",
                        "mitigation": "无",
                    },
                    {
                        "risk": "流动性风险",
                        "probability": "低",
                        "impact": "高",
                        "mitigation": "分散",
                    },
                ],
                "key_disagreements": [],
                "conflict_resolution": "ok",
            },
        )
    call_args = mock_judge_container.judge_service().run.call_args[0][0]
    assert call_args.risk_factors == ["政策风险", "流动性风险"]


@pytest.mark.asyncio
async def test_return_value_is_dict_serialization(mock_judge_container):
    """run_verdict 返回 VerdictDTO 的 dict（.model_dump()）。"""
    with patch(
        "src.modules.coordinator.infrastructure.adapters.judge_gateway_adapter.JudgeContainer",
        return_value=mock_judge_container,
    ):
        adapter = JudgeGatewayAdapter(_mock_session_factory())
        result = await adapter.run_verdict(
            symbol="000001.SZ",
            debate_outcome={
                "direction": "BULLISH",
                "confidence": 0.7,
                "bull_case": {"core_thesis": "a"},
                "bear_case": {"core_thesis": "b"},
                "risk_matrix": [],
                "key_disagreements": [],
                "conflict_resolution": "ok",
            },
        )
    assert isinstance(result, dict)
    assert result["symbol"] == "000001.SZ"
    assert result["action"] == "BUY"
    assert result["position_percent"] == 0.3
