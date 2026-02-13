"""Debate REST 端点集成测试：正常请求 200、symbol 缺失 400、expert_results 为空 400。"""
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app
from src.modules.debate.presentation.rest.debate_router import get_debate_service


@pytest.fixture
def mock_debate_outcome_dto():
    """模拟 DebateOutcomeDTO。"""
    from src.modules.debate.application.dtos.debate_outcome_dto import (
        BearCaseDTO,
        BullCaseDTO,
        DebateOutcomeDTO,
    )
    from src.modules.debate.domain.dtos.risk_matrix import RiskItemDTO
    return DebateOutcomeDTO(
        symbol="000001.SZ",
        direction="NEUTRAL",
        confidence=0.6,
        bull_case=BullCaseDTO(
            core_thesis="多",
            supporting_arguments=[],
            acknowledged_risks=[],
        ),
        bear_case=BearCaseDTO(
            core_thesis="空",
            supporting_arguments=[],
            acknowledged_strengths=[],
        ),
        risk_matrix=[RiskItemDTO(risk="R", probability="中", impact="高", mitigation="")],
        key_disagreements=[],
        conflict_resolution="中性",
    )


@pytest.fixture
def mock_debate_service(mock_debate_outcome_dto):
    """Mock DebateService.run 返回固定 DTO。"""
    svc = MagicMock()
    svc.run = AsyncMock(return_value=mock_debate_outcome_dto)
    return svc


@pytest.mark.asyncio
async def test_post_debate_run_returns_200(mock_debate_service):
    """正常 POST /api/v1/debate/run 返回 200，响应含 direction、confidence、risk_matrix。"""
    async def override_get_debate_service():
        return mock_debate_service
    app.dependency_overrides[get_debate_service] = override_get_debate_service
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            resp = await client.post(
                "/api/v1/debate/run",
                json={
                    "symbol": "000001.SZ",
                    "expert_results": {
                        "technical_analyst": {
                            "signal": "BULLISH",
                            "confidence": 0.8,
                            "summary_reasoning": "技术偏多",
                            "risk_warning": "无",
                        },
                    },
                },
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["symbol"] == "000001.SZ"
        assert data["direction"] == "NEUTRAL"
        assert data["confidence"] == 0.6
        assert "risk_matrix" in data
        assert len(data["risk_matrix"]) == 1
    finally:
        app.dependency_overrides.pop(get_debate_service, None)


@pytest.mark.asyncio
async def test_post_debate_run_symbol_missing_returns_400():
    """symbol 缺失或空时返回 400。"""
    async def override_get_debate_service():
        return MagicMock()
    app.dependency_overrides[get_debate_service] = override_get_debate_service
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            resp = await client.post(
                "/api/v1/debate/run",
                json={"symbol": "", "expert_results": {"ta": {"signal": "BULLISH", "confidence": 0.8, "reasoning": "", "risk_warning": ""}}},
            )
        assert resp.status_code == 400
    finally:
        app.dependency_overrides.pop(get_debate_service, None)


@pytest.mark.asyncio
async def test_post_debate_run_expert_results_empty_returns_400():
    """expert_results 为空时返回 400。"""
    async def override_get_debate_service():
        return MagicMock()
    app.dependency_overrides[get_debate_service] = override_get_debate_service
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            resp = await client.post(
                "/api/v1/debate/run",
                json={"symbol": "000001.SZ", "expert_results": {}},
            )
        assert resp.status_code == 400
    finally:
        app.dependency_overrides.pop(get_debate_service, None)
