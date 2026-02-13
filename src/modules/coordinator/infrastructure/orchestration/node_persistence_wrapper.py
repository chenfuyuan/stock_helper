"""
节点执行持久化包装：包装 LangGraph 节点函数，在执行前后记录 NodeExecution。

写入失败不阻塞主流程，仅记录 error 日志。
"""
import logging
from collections.abc import Callable
from datetime import datetime
from typing import Any
from uuid import uuid4

from src.shared.infrastructure.execution_context import current_execution_ctx
from src.modules.coordinator.domain.model.node_execution import NodeExecution
from src.modules.coordinator.domain.ports.research_session_repository import IResearchSessionRepository
from src.modules.coordinator.infrastructure.orchestration.graph_state import ResearchGraphState

logger = logging.getLogger(__name__)


def _extract_result_and_narrative(node_type: str, return_value: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
    """从节点返回值中提取 result_data 与 narrative_report。"""
    result_data: dict[str, Any] | None = None
    narrative_report = ""

    if node_type in (
        "technical_analyst",
        "financial_auditor",
        "valuation_modeler",
        "macro_intelligence",
        "catalyst_detective",
    ):
        results = return_value.get("results") or {}
        data = results.get(node_type)
        if isinstance(data, dict):
            result_data = data
            narrative_report = (data.get("narrative_report") or "") or ""
    elif node_type == "debate":
        outcome = return_value.get("debate_outcome")
        if isinstance(outcome, dict):
            result_data = outcome
            narrative_report = (outcome.get("narrative_report") or "") or ""
    elif node_type == "judge":
        verdict = return_value.get("verdict")
        if isinstance(verdict, dict):
            result_data = verdict
            narrative_report = (verdict.get("narrative_report") or "") or ""

    return result_data, narrative_report


def persist_node_execution(
    node_fn: Callable[[ResearchGraphState], Any],
    node_type: str,
    session_repo: IResearchSessionRepository,
) -> Callable[[ResearchGraphState], Any]:
    """
    包装节点函数：记录 started_at → 执行 → 成功时记录 result/narrative，失败时记录 error → 写入 NodeExecution。
    写入失败不阻塞，仅打 warning。
    """

    async def wrapper(state: ResearchGraphState) -> dict[str, Any]:
        ctx = current_execution_ctx.get()
        if not ctx:
            return await node_fn(state)

        from uuid import UUID
        session_id = UUID(ctx.session_id)
        started_at = datetime.utcnow()
        execution = NodeExecution(
            id=uuid4(),
            session_id=session_id,
            node_type=node_type,
            status="success",
            started_at=started_at,
        )
        try:
            result = await node_fn(state)
            completed_at = datetime.utcnow()
            duration_ms = int((completed_at - started_at).total_seconds() * 1000)
            result_data, narrative_report = _extract_result_and_narrative(node_type, result)
            execution.mark_success(
                result_data=result_data or {},
                narrative_report=narrative_report,
                completed_at=completed_at,
                duration_ms=duration_ms,
            )
            try:
                await session_repo.save_node_execution(execution)
            except Exception as e:
                logger.warning("节点执行记录写入失败，不阻塞主流程: %s", e)
            return result
        except Exception as e:
            completed_at = datetime.utcnow()
            duration_ms = int((completed_at - started_at).total_seconds() * 1000)
            execution.mark_failed(
                error_type=type(e).__name__,
                error_message=str(e),
                completed_at=completed_at,
                duration_ms=duration_ms,
            )
            try:
                await session_repo.save_node_execution(execution)
            except Exception as save_err:
                logger.warning("节点失败记录写入失败，不阻塞主流程: %s", save_err)
            raise

    wrapper.__name__ = getattr(node_fn, "__name__", f"persisted_{node_type}")
    return wrapper
