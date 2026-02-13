"""
ResearchOrchestrationService 测试：入参校验、按需路由、单专家失败降级、全部失败、全部成功。
"""
import pytest

from src.modules.coordinator.application.research_orchestration_service import (
    ResearchOrchestrationService,
)
from src.modules.coordinator.domain.exceptions import AllExpertsFailedError
from src.modules.coordinator.domain.model.enums import ExpertType
from src.modules.coordinator.domain.ports.research_expert_gateway import (
    IResearchExpertGateway,
)
from src.modules.coordinator.infrastructure.orchestration.langgraph_orchestrator import (
    LangGraphResearchOrchestrator,
)
from src.shared.domain.exceptions import BadRequestException


def _make_service(gateway: IResearchExpertGateway) -> ResearchOrchestrationService:
    orchestrator = LangGraphResearchOrchestrator(gateway)
    return ResearchOrchestrationService(orchestrator)


# ---------- 8.2 入参校验 ----------
@pytest.mark.asyncio
async def test_symbol_missing_raises_bad_request(mock_research_expert_gateway):
    """symbol 缺失时抛出 BadRequestException。"""
    service = _make_service(mock_research_expert_gateway)
    with pytest.raises(BadRequestException) as exc_info:
        await service.execute(symbol="", experts=["technical_analyst"])
    assert "symbol" in exc_info.value.message.lower() or "必填" in exc_info.value.message


@pytest.mark.asyncio
async def test_experts_empty_raises_bad_request(mock_research_expert_gateway):
    """experts 为空时抛出 BadRequestException。"""
    service = _make_service(mock_research_expert_gateway)
    with pytest.raises(BadRequestException) as exc_info:
        await service.execute(symbol="000001.SZ", experts=[])
    assert "experts" in exc_info.value.message.lower() or "必填" in exc_info.value.message


@pytest.mark.asyncio
async def test_experts_invalid_value_raises_bad_request(mock_research_expert_gateway):
    """experts 含非法值时抛出 BadRequestException。"""
    service = _make_service(mock_research_expert_gateway)
    with pytest.raises(BadRequestException) as exc_info:
        await service.execute(
            symbol="000001.SZ",
            experts=["unknown_expert"],
        )
    assert "unknown_expert" in exc_info.value.message or "非法" in exc_info.value.message


# ---------- 8.3 按需路由 ----------
@pytest.mark.asyncio
async def test_only_selected_experts_called(mock_research_expert_gateway):
    """指定 2 个专家时，仅这 2 个专家的 run_expert 被调用。"""
    service = _make_service(mock_research_expert_gateway)
    await service.execute(
        symbol="000001.SZ",
        experts=["macro_intelligence", "catalyst_detective"],
    )
    assert mock_research_expert_gateway.run_expert.call_count == 2
    call_args_list = mock_research_expert_gateway.run_expert.call_args_list
    expert_types_called = {call.kwargs["expert_type"] for call in call_args_list}
    assert expert_types_called == {
        ExpertType.MACRO_INTELLIGENCE,
        ExpertType.CATALYST_DETECTIVE,
    }


# ---------- 8.4 单专家失败降级 ----------
@pytest.mark.asyncio
async def test_single_expert_failure_partial_status(mock_gateway_with_failure):
    """某专家失败时 overall_status 为 partial，成功专家 data 正常，失败专家 error 记录。"""
    service = _make_service(mock_gateway_with_failure)
    result = await service.execute(
        symbol="000001.SZ",
        experts=["technical_analyst", "macro_intelligence"],
    )
    assert result.overall_status == "partial"
    ta_item = next(r for r in result.expert_results if r.expert_type == ExpertType.TECHNICAL_ANALYST)
    assert ta_item.status == "failed"
    assert ta_item.error is not None
    mi_item = next(r for r in result.expert_results if r.expert_type == ExpertType.MACRO_INTELLIGENCE)
    assert mi_item.status == "success"
    assert mi_item.data is not None


# ---------- 8.5 全部专家失败 ----------
@pytest.mark.asyncio
async def test_all_experts_fail_raises_all_experts_failed(mock_gateway_all_fail):
    """全部专家失败时抛出 AllExpertsFailedError。"""
    service = _make_service(mock_gateway_all_fail)
    with pytest.raises(AllExpertsFailedError):
        await service.execute(
            symbol="000001.SZ",
            experts=["technical_analyst", "macro_intelligence"],
        )


# ---------- 8.7 全部成功 ----------
@pytest.mark.asyncio
async def test_all_success_completed_status(mock_research_expert_gateway):
    """全部专家成功时 overall_status 为 completed，所有专家 data 正确。"""
    service = _make_service(mock_research_expert_gateway)
    result = await service.execute(
        symbol="000001.SZ",
        experts=["valuation_modeler", "financial_auditor"],
    )
    assert result.overall_status == "completed"
    assert len(result.expert_results) == 2
    for item in result.expert_results:
        assert item.status == "success"
        assert item.data is not None
        assert item.data.get("signal") == "NEUTRAL"
