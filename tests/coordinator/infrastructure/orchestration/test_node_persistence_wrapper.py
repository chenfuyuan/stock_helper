"""
任务 12.6：测试持久化写入失败不阻塞主流程。

当 session_repo.save_node_execution 抛异常时，包装器仍应返回节点结果或抛出节点异常，不因写入失败而阻塞。
"""
from unittest.mock import AsyncMock

import pytest

from src.modules.coordinator.infrastructure.orchestration.node_persistence_wrapper import (
    persist_node_execution,
)
from src.modules.coordinator.infrastructure.orchestration.graph_state import ResearchGraphState


@pytest.fixture
def mock_session_repo():
    """Mock IResearchSessionRepository。"""
    repo = AsyncMock()
    return repo


@pytest.mark.asyncio
async def test_persistence_failure_on_success_does_not_block_return(
    mock_session_repo,
):
    """节点成功时，若 save_node_execution 抛异常，仍返回节点结果，不阻塞。"""
    mock_session_repo.save_node_execution = AsyncMock(side_effect=RuntimeError("DB 不可用"))

    async def happy_node(state: ResearchGraphState) -> dict:
        return {"results": {"technical_analyst": {"signal": "BULLISH", "narrative_report": "多"}}}

    wrapped = persist_node_execution(happy_node, "technical_analyst", mock_session_repo)

    from src.shared.infrastructure.execution_context import (
        ExecutionContext,
        current_execution_ctx,
    )
    token = current_execution_ctx.set(ExecutionContext(session_id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"))
    try:
        state = ResearchGraphState(symbol="AAPL", selected_experts=["technical_analyst"])
        result = await wrapped(state)
        assert result["results"]["technical_analyst"]["signal"] == "BULLISH"
    finally:
        current_execution_ctx.reset(token)


@pytest.mark.asyncio
async def test_persistence_failure_on_node_failure_reraises_node_exception(
    mock_session_repo,
):
    """节点抛异常时，若 save_node_execution（写入失败记录）也抛异常，应抛出节点异常而非写入异常。"""
    mock_session_repo.save_node_execution = AsyncMock(side_effect=RuntimeError("DB 写入失败"))

    async def failing_node(state: ResearchGraphState) -> dict:
        raise ValueError("节点执行失败")

    wrapped = persist_node_execution(failing_node, "judge", mock_session_repo)

    from src.shared.infrastructure.execution_context import (
        ExecutionContext,
        current_execution_ctx,
    )
    token = current_execution_ctx.set(ExecutionContext(session_id="bbbbbbbb-cccc-dddd-eeee-ffffffffffff"))
    try:
        state = ResearchGraphState(symbol="MSFT", selected_experts=[])
        with pytest.raises(ValueError, match="节点执行失败"):
            await wrapped(state)
    finally:
        current_execution_ctx.reset(token)
