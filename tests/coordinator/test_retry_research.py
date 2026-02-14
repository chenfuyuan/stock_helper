"""
研究任务重试测试：retry() 方法的校验、专家分离、编排器 pre_populated_results 支持、REST 端点。
"""

from datetime import datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.modules.coordinator.application.research_orchestration_service import (
    ResearchOrchestrationService,
)
from src.modules.coordinator.domain.dtos.research_dtos import (
    ExpertResultItem,
    ResearchRequest,
    ResearchResult,
)
from src.modules.coordinator.domain.exceptions import (
    SessionNotFoundError,
    SessionNotRetryableError,
)
from src.modules.coordinator.domain.model.enums import ExpertType
from src.modules.coordinator.domain.model.node_execution import NodeExecution
from src.modules.coordinator.domain.model.research_session import (
    ResearchSession,
)
from src.modules.coordinator.domain.ports.research_orchestration import (
    IResearchOrchestrationPort,
)
from src.modules.coordinator.domain.ports.research_session_repository import (
    IResearchSessionRepository,
)

# ---------- Fixtures ----------


def _make_session(
    status: str = "partial",
    experts: list[str] | None = None,
    retry_count: int = 0,
) -> ResearchSession:
    """构造一个测试用 ResearchSession。"""
    return ResearchSession(
        id=uuid4(),
        symbol="000001.SZ",
        status=status,
        selected_experts=experts
        or ["technical_analyst", "macro_intelligence", "financial_auditor"],
        options={},
        trigger_source="api",
        created_at=datetime.utcnow(),
        retry_count=retry_count,
    )


def _make_node_execution(
    session_id,
    node_type: str,
    status: str = "success",
    result_data: dict | None = None,
) -> NodeExecution:
    """构造一个测试用 NodeExecution。"""
    ne = NodeExecution(
        id=uuid4(),
        session_id=session_id,
        node_type=node_type,
        status=status,
        started_at=datetime.utcnow(),
    )
    if status == "success":
        ne.result_data = result_data or {
            "signal": "NEUTRAL",
            "confidence": 0.8,
        }
    elif status == "failed":
        ne.error_type = "RuntimeError"
        ne.error_message = f"{node_type} 执行失败"
    return ne


def _make_mock_session_repo(
    session: ResearchSession | None = None,
    node_executions: list[NodeExecution] | None = None,
) -> AsyncMock:
    """构造 mock IResearchSessionRepository。"""
    repo = AsyncMock(spec=IResearchSessionRepository)
    repo.get_session_by_id = AsyncMock(return_value=session)
    repo.get_node_executions_by_session = AsyncMock(
        return_value=node_executions or []
    )
    repo.save_session = AsyncMock()
    repo.update_session = AsyncMock()
    repo.save_node_execution = AsyncMock()
    return repo


def _make_mock_orchestration_port(
    overall_status: str = "completed",
) -> AsyncMock:
    """构造 mock IResearchOrchestrationPort，返回预设的 ResearchResult。"""
    port = AsyncMock(spec=IResearchOrchestrationPort)

    async def mock_run(request: ResearchRequest) -> ResearchResult:
        expert_results = []
        # 预填充的专家（复用的成功结果）
        pre = request.pre_populated_results or {}
        for expert_value, data in pre.items():
            expert_results.append(
                ExpertResultItem(
                    expert_type=ExpertType(expert_value),
                    status="success",
                    data=data,
                )
            )
        # 本次执行的专家
        for et in request.experts:
            expert_results.append(
                ExpertResultItem(
                    expert_type=et,
                    status="success",
                    data={"signal": "BULLISH", "confidence": 0.9},
                )
            )
        return ResearchResult(
            symbol=request.symbol,
            overall_status=overall_status,
            expert_results=expert_results,
            session_id=str(uuid4()),
            retry_count=request.retry_count,
        )

    port.run = mock_run
    return port


# ========== 6.1 retry() — session 不存在抛异常 ==========


@pytest.mark.asyncio
async def test_retry_session_not_found():
    """session 不存在时抛出 SessionNotFoundError。"""
    repo = _make_mock_session_repo(session=None)
    port = _make_mock_orchestration_port()
    service = ResearchOrchestrationService(port, session_repo=repo)

    with pytest.raises(SessionNotFoundError):
        await service.retry(session_id=uuid4())


# ========== 6.2 retry() — session 状态为 completed / running 时拒绝 ==========


@pytest.mark.asyncio
async def test_retry_completed_session_raises_not_retryable():
    """session 状态为 completed 时抛出 SessionNotRetryableError。"""
    session = _make_session(status="completed")
    repo = _make_mock_session_repo(session=session)
    port = _make_mock_orchestration_port()
    service = ResearchOrchestrationService(port, session_repo=repo)

    with pytest.raises(SessionNotRetryableError) as exc_info:
        await service.retry(session_id=session.id)
    assert exc_info.value.status_code == 400
    assert "已完成" in exc_info.value.message


@pytest.mark.asyncio
async def test_retry_running_session_raises_not_retryable():
    """session 状态为 running 时抛出 SessionNotRetryableError，status_code=409。"""
    session = _make_session(status="running")
    repo = _make_mock_session_repo(session=session)
    port = _make_mock_orchestration_port()
    service = ResearchOrchestrationService(port, session_repo=repo)

    with pytest.raises(SessionNotRetryableError) as exc_info:
        await service.retry(session_id=session.id)
    assert exc_info.value.status_code == 409
    assert "执行中" in exc_info.value.message


# ========== 6.3 retry() — 正确分离成功/失败专家 ==========


@pytest.mark.asyncio
async def test_retry_separates_success_and_failed_experts():
    """retry() 正确分离成功/失败专家，构建含 pre_populated_results 的 ResearchRequest。"""
    session = _make_session(status="partial")
    node_executions = [
        _make_node_execution(
            session.id,
            "technical_analyst",
            status="success",
            result_data={"signal": "BULLISH", "confidence": 0.85},
        ),
        _make_node_execution(
            session.id, "macro_intelligence", status="failed"
        ),
        _make_node_execution(
            session.id,
            "financial_auditor",
            status="success",
            result_data={"signal": "NEUTRAL", "confidence": 0.7},
        ),
    ]
    repo = _make_mock_session_repo(
        session=session, node_executions=node_executions
    )

    # 用可记录调用参数的 mock port
    captured_request: list[ResearchRequest] = []

    async def capture_run(request: ResearchRequest) -> ResearchResult:
        captured_request.append(request)
        return ResearchResult(
            symbol=request.symbol,
            overall_status="completed",
            expert_results=[
                ExpertResultItem(
                    expert_type=ExpertType.TECHNICAL_ANALYST,
                    status="success",
                    data={"signal": "BULLISH", "confidence": 0.85},
                ),
                ExpertResultItem(
                    expert_type=ExpertType.MACRO_INTELLIGENCE,
                    status="success",
                    data={"signal": "NEUTRAL", "confidence": 0.9},
                ),
                ExpertResultItem(
                    expert_type=ExpertType.FINANCIAL_AUDITOR,
                    status="success",
                    data={"signal": "NEUTRAL", "confidence": 0.7},
                ),
            ],
            session_id=str(uuid4()),
            retry_count=request.retry_count,
        )

    port = AsyncMock(spec=IResearchOrchestrationPort)
    port.run = capture_run
    service = ResearchOrchestrationService(port, session_repo=repo)

    result = await service.retry(session_id=session.id)

    # 验证构建的 ResearchRequest
    assert len(captured_request) == 1
    req = captured_request[0]
    # 仅失败的专家
    assert req.experts == [ExpertType.MACRO_INTELLIGENCE]
    # pre_populated_results 包含成功的专家
    assert "technical_analyst" in req.pre_populated_results
    assert "financial_auditor" in req.pre_populated_results
    assert len(req.pre_populated_results) == 2
    # parent_session_id 和 retry_count
    assert req.parent_session_id == session.id
    assert req.retry_count == 1

    # 验证最终结果
    assert result.overall_status == "completed"


# ========== 6.4 编排器 — pre_populated_results 注入图初始状态 ==========


@pytest.mark.asyncio
async def test_orchestrator_pre_populated_results_injected(
    mock_research_expert_gateway,
):
    """pre_populated_results 注入图初始状态，仅失败专家被执行。"""
    pytest.importorskip(
        "langgraph", reason="langgraph 未安装，跳过编排器集成测试"
    )
    from src.modules.coordinator.infrastructure.orchestration.langgraph_orchestrator import (
        LangGraphResearchOrchestrator,
    )

    orchestrator = LangGraphResearchOrchestrator(mock_research_expert_gateway)
    pre_results = {
        "technical_analyst": {"signal": "BULLISH", "confidence": 0.85},
        "financial_auditor": {"signal": "NEUTRAL", "confidence": 0.7},
    }
    request = ResearchRequest(
        symbol="000001.SZ",
        experts=[ExpertType.MACRO_INTELLIGENCE],  # 仅重试这一个
        pre_populated_results=pre_results,
        parent_session_id=uuid4(),
        retry_count=1,
    )
    result = await orchestrator.run(request)

    # macro_intelligence 被执行
    assert mock_research_expert_gateway.run_expert.call_count == 1
    call_kwargs = mock_research_expert_gateway.run_expert.call_args
    assert call_kwargs.kwargs["expert_type"] == ExpertType.MACRO_INTELLIGENCE

    # expert_results 包含全部 3 个专家（2 个复用 + 1 个新执行）
    assert len(result.expert_results) == 3
    expert_map = {er.expert_type.value: er for er in result.expert_results}
    assert expert_map["technical_analyst"].status == "success"
    assert expert_map["financial_auditor"].status == "success"
    assert expert_map["macro_intelligence"].status == "success"

    # retry_count 正确
    assert result.retry_count == 1


# ========== 6.5 编排器 — pre_populated_results 为 None 时行为不变 ==========


@pytest.mark.asyncio
async def test_orchestrator_no_pre_populated_results(
    mock_research_expert_gateway,
):
    """pre_populated_results 为 None 时，行为与改动前一致。"""
    pytest.importorskip(
        "langgraph", reason="langgraph 未安装，跳过编排器集成测试"
    )
    from src.modules.coordinator.infrastructure.orchestration.langgraph_orchestrator import (
        LangGraphResearchOrchestrator,
    )

    orchestrator = LangGraphResearchOrchestrator(mock_research_expert_gateway)
    request = ResearchRequest(
        symbol="000001.SZ",
        experts=[ExpertType.TECHNICAL_ANALYST, ExpertType.MACRO_INTELLIGENCE],
    )
    result = await orchestrator.run(request)

    assert mock_research_expert_gateway.run_expert.call_count == 2
    assert len(result.expert_results) == 2
    assert result.retry_count == 0
    assert result.overall_status == "completed"


# ========== 6.6 集成测试：POST /research/{session_id}/retry ==========


@pytest.mark.asyncio
async def test_retry_endpoint_partial_session():
    """对 partial session 重试后返回完整结果。"""
    pytest.importorskip(
        "langgraph", reason="langgraph 未安装，跳过端点集成测试"
    )
    from fastapi import FastAPI
    from httpx import ASGITransport, AsyncClient

    from src.modules.coordinator.presentation.rest.research_routes import (
        router,
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/v1/coordinator")

    session = _make_session(status="partial")
    node_executions = [
        _make_node_execution(
            session.id,
            "technical_analyst",
            status="success",
            result_data={"signal": "BULLISH", "confidence": 0.85},
        ),
        _make_node_execution(
            session.id, "macro_intelligence", status="failed"
        ),
    ]
    mock_repo = _make_mock_session_repo(
        session=session, node_executions=node_executions
    )
    mock_port = _make_mock_orchestration_port(overall_status="completed")
    mock_service = ResearchOrchestrationService(
        mock_port, session_repo=mock_repo
    )

    async def override_service():
        return mock_service

    from src.modules.coordinator.presentation.rest.research_routes import (
        get_research_orchestration_service,
    )

    app.dependency_overrides[get_research_orchestration_service] = (
        override_service
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        resp = await client.post(
            f"/api/v1/coordinator/research/{session.id}/retry"
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["overall_status"] == "completed"
    assert data["retry_count"] == 1
    assert "technical_analyst" in data["expert_results"]
    assert "macro_intelligence" in data["expert_results"]


# ========== 6.7 集成测试：404 / 400 / 409 错误码 ==========


@pytest.mark.asyncio
async def test_retry_endpoint_session_not_found():
    """session 不存在时返回 404。"""
    pytest.importorskip(
        "langgraph", reason="langgraph 未安装，跳过端点集成测试"
    )
    from fastapi import FastAPI
    from httpx import ASGITransport, AsyncClient

    from src.modules.coordinator.presentation.rest.research_routes import (
        get_research_orchestration_service,
        router,
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/v1/coordinator")

    mock_repo = _make_mock_session_repo(session=None)
    mock_port = _make_mock_orchestration_port()
    mock_service = ResearchOrchestrationService(
        mock_port, session_repo=mock_repo
    )

    async def override_service():
        return mock_service

    app.dependency_overrides[get_research_orchestration_service] = (
        override_service
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        resp = await client.post(
            f"/api/v1/coordinator/research/{uuid4()}/retry"
        )

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_retry_endpoint_completed_session_returns_400():
    """completed session 返回 400。"""
    pytest.importorskip(
        "langgraph", reason="langgraph 未安装，跳过端点集成测试"
    )
    from fastapi import FastAPI
    from httpx import ASGITransport, AsyncClient

    from src.modules.coordinator.presentation.rest.research_routes import (
        get_research_orchestration_service,
        router,
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/v1/coordinator")

    session = _make_session(status="completed")
    mock_repo = _make_mock_session_repo(session=session)
    mock_port = _make_mock_orchestration_port()
    mock_service = ResearchOrchestrationService(
        mock_port, session_repo=mock_repo
    )

    async def override_service():
        return mock_service

    app.dependency_overrides[get_research_orchestration_service] = (
        override_service
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        resp = await client.post(
            f"/api/v1/coordinator/research/{session.id}/retry"
        )

    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_retry_endpoint_running_session_returns_409():
    """running session 返回 409。"""
    pytest.importorskip(
        "langgraph", reason="langgraph 未安装，跳过端点集成测试"
    )
    from fastapi import FastAPI
    from httpx import ASGITransport, AsyncClient

    from src.modules.coordinator.presentation.rest.research_routes import (
        get_research_orchestration_service,
        router,
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/v1/coordinator")

    session = _make_session(status="running")
    mock_repo = _make_mock_session_repo(session=session)
    mock_port = _make_mock_orchestration_port()
    mock_service = ResearchOrchestrationService(
        mock_port, session_repo=mock_repo
    )

    async def override_service():
        return mock_service

    app.dependency_overrides[get_research_orchestration_service] = (
        override_service
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        resp = await client.post(
            f"/api/v1/coordinator/research/{session.id}/retry"
        )

    assert resp.status_code == 409


# ========== 6.8 ResearchResult / Response 包含 retry_count ==========


def test_research_result_has_retry_count():
    """ResearchResult 包含 retry_count 字段，默认为 0。"""
    result = ResearchResult(
        symbol="000001.SZ",
        overall_status="completed",
        expert_results=[],
    )
    assert result.retry_count == 0

    result_with_retry = ResearchResult(
        symbol="000001.SZ",
        overall_status="completed",
        expert_results=[],
        retry_count=2,
    )
    assert result_with_retry.retry_count == 2


def test_research_orchestration_response_has_retry_count():
    """ResearchOrchestrationResponse 包含 retry_count 字段。"""
    pytest.importorskip(
        "langgraph", reason="langgraph 未安装，跳过响应模型测试"
    )
    from src.modules.coordinator.presentation.rest.research_routes import (
        ResearchOrchestrationResponse,
    )

    resp = ResearchOrchestrationResponse(
        symbol="000001.SZ",
        overall_status="completed",
        expert_results={},
    )
    assert resp.retry_count == 0

    resp_with_retry = ResearchOrchestrationResponse(
        symbol="000001.SZ",
        overall_status="completed",
        expert_results={},
        retry_count=3,
    )
    assert resp_with_retry.retry_count == 3
