"""Judge REST 端点集成测试：正常请求返回 200、symbol 缺失返回 400、debate_outcome 为空返回 400。"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app
from src.modules.judge.presentation.rest.judge_router import get_judge_service


@pytest.fixture
def mock_verdict_dto():
    """模拟 VerdictDTO。"""
    from src.modules.judge.application.dtos.verdict_dto import VerdictDTO

    return VerdictDTO(
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


@pytest.fixture
def mock_judge_service(mock_verdict_dto):
    """Mock JudgeService.run 返回固定 VerdictDTO。"""
    svc = MagicMock()
    svc.run = AsyncMock(return_value=mock_verdict_dto)
    return svc


@pytest.mark.asyncio
async def test_post_judge_verdict_returns_200(mock_judge_service):
    """正常 POST /api/v1/judge/verdict 返回 200，响应含 action、position_percent、confidence。"""

    async def override_get_judge_service():
        return mock_judge_service

    app.dependency_overrides[get_judge_service] = override_get_judge_service
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            resp = await client.post(
                "/api/v1/judge/verdict",
                json={
                    "symbol": "000001.SZ",
                    "debate_outcome": {
                        "direction": "BULLISH",
                        "confidence": 0.7,
                        "bull_case": {"core_thesis": "估值偏低"},
                        "bear_case": {"core_thesis": "景气度下行"},
                        "risk_matrix": [{"risk": "政策"}],
                        "key_disagreements": ["估值分歧"],
                        "conflict_resolution": "综合偏多",
                    },
                },
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["symbol"] == "000001.SZ"
        assert data["action"] == "BUY"
        assert data["position_percent"] == 0.3
        assert data["confidence"] == 0.72
        assert "risk_warnings" in data
    finally:
        app.dependency_overrides.pop(get_judge_service, None)


@pytest.mark.asyncio
async def test_post_judge_verdict_symbol_missing_returns_400():
    """symbol 缺失或空时返回 400。"""

    async def override_get_judge_service():
        return MagicMock()

    app.dependency_overrides[get_judge_service] = override_get_judge_service
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            resp = await client.post(
                "/api/v1/judge/verdict",
                json={
                    "symbol": "",
                    "debate_outcome": {
                        "direction": "BULLISH",
                        "confidence": 0.7,
                    },
                },
            )
        assert resp.status_code == 400
    finally:
        app.dependency_overrides.pop(get_judge_service, None)


@pytest.mark.asyncio
async def test_post_judge_verdict_debate_outcome_empty_returns_400():
    """debate_outcome 为空时返回 400。"""

    async def override_get_judge_service():
        return MagicMock()

    app.dependency_overrides[get_judge_service] = override_get_judge_service
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            resp = await client.post(
                "/api/v1/judge/verdict",
                json={"symbol": "000001.SZ", "debate_outcome": {}},
            )
        assert resp.status_code == 400
    finally:
        app.dependency_overrides.pop(get_judge_service, None)
