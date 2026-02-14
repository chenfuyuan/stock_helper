"""
ResearchGatewayAdapter 测试：按 ExpertType 正确调度到对应 Research Service 并传参。
"""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.modules.coordinator.domain.model.enums import ExpertType
from src.modules.coordinator.infrastructure.adapters.research_gateway_adapter import (
    ResearchGatewayAdapter,
)


class _MockAsyncSessionContext:
    """模拟 async with session_factory() as session 的上下文管理器。"""

    async def __aenter__(self):
        return MagicMock()

    async def __aexit__(self, *args):
        pass


def _mock_session_factory():
    """返回可 async with 的 mock session 上下文。"""
    return _MockAsyncSessionContext()


@pytest.fixture
def mock_research_container():
    """Mock ResearchContainer，各 service 返回 mock。"""
    container = MagicMock()
    for expert_type in ExpertType:
        svc = MagicMock()
        svc.run = AsyncMock(return_value={"result": f"mock_{expert_type.value}"})
        method_name = f"{expert_type.value}_service"
        getattr(container, method_name).return_value = svc
    return container


@pytest.fixture
def adapter(mock_research_container):
    """Adapter 使用 mock session factory，并 patch ResearchContainer 返回 mock。"""
    with patch(
        "src.modules.coordinator.infrastructure.adapters.research_gateway_adapter.ResearchContainer",
        return_value=mock_research_container,
    ):
        yield ResearchGatewayAdapter(_mock_session_factory)


@pytest.mark.asyncio
async def test_technical_analyst_dispatch(adapter, mock_research_container):
    """Technical analyst：传 ticker、analysis_date。"""
    svc = mock_research_container.technical_analyst_service()
    result = await adapter.run_expert(
        ExpertType.TECHNICAL_ANALYST,
        symbol="000001.SZ",
        options={"technical_analyst": {"analysis_date": "2026-02-13"}},
    )
    svc.run.assert_called_once_with(
        ticker="000001.SZ",
        analysis_date=date(2026, 2, 13),
    )
    assert result["result"] == "mock_technical_analyst"


@pytest.mark.asyncio
async def test_financial_auditor_dispatch(adapter, mock_research_container):
    """Financial auditor：传 symbol、limit。"""
    svc = mock_research_container.financial_auditor_service()
    result = await adapter.run_expert(
        ExpertType.FINANCIAL_AUDITOR,
        symbol="000001.SZ",
        options={"financial_auditor": {"limit": 3}},
    )
    svc.run.assert_called_once_with(symbol="000001.SZ", limit=3)
    assert result["result"] == "mock_financial_auditor"


@pytest.mark.asyncio
async def test_valuation_modeler_dispatch(adapter, mock_research_container):
    """Valuation modeler：仅 symbol。"""
    svc = mock_research_container.valuation_modeler_service()
    result = await adapter.run_expert(
        ExpertType.VALUATION_MODELER,
        symbol="000001.SZ",
    )
    svc.run.assert_called_once_with(symbol="000001.SZ")
    assert result["result"] == "mock_valuation_modeler"


@pytest.mark.asyncio
async def test_macro_intelligence_dispatch(adapter, mock_research_container):
    """Macro intelligence：仅 symbol。"""
    svc = mock_research_container.macro_intelligence_service()
    result = await adapter.run_expert(
        ExpertType.MACRO_INTELLIGENCE,
        symbol="000001.SZ",
    )
    svc.run.assert_called_once_with(symbol="000001.SZ")
    assert result["result"] == "mock_macro_intelligence"


@pytest.mark.asyncio
async def test_catalyst_detective_dispatch(adapter, mock_research_container):
    """Catalyst detective：仅 symbol，Service 直接返回 dict，无需 Adapter 再归一化。"""
    svc = mock_research_container.catalyst_detective_service()
    svc.run = AsyncMock(
        return_value={
            "result": {"catalyst_assessment": "Neutral (中性)"},
            "raw_llm_output": "raw",
            "user_prompt": "prompt",
            "catalyst_context": {},
        }
    )

    result = await adapter.run_expert(
        ExpertType.CATALYST_DETECTIVE,
        symbol="000001.SZ",
    )
    svc.run.assert_called_once_with(symbol="000001.SZ")
    assert "result" in result
    assert "raw_llm_output" in result
    assert "user_prompt" in result
    assert result["raw_llm_output"] == "raw"
