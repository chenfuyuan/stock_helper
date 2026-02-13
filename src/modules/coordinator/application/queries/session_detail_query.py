"""
会话详情查询用例：按 session_id 返回会话及全部节点执行记录。
"""
from uuid import UUID

from src.modules.coordinator.application.dtos.session_dtos import (
    NodeExecutionItemDTO,
    SessionDetailDTO,
)
from src.modules.coordinator.domain.ports.research_session_repository import IResearchSessionRepository


class SessionDetailQuery:
    """查询单次研究会话详情（含 NodeExecution 列表）。"""

    def __init__(self, session_repo: IResearchSessionRepository) -> None:
        self._repo = session_repo

    async def execute(self, session_id: UUID) -> SessionDetailDTO | None:
        """返回会话详情及节点执行列表；不存在则返回 None。"""
        session = await self._repo.get_session_by_id(session_id)
        if session is None:
            return None
        executions = await self._repo.get_node_executions_by_session(session_id)
        return SessionDetailDTO(
            id=str(session.id),
            symbol=session.symbol,
            status=session.status,
            selected_experts=session.selected_experts,
            options=session.options,
            trigger_source=session.trigger_source,
            created_at=session.created_at,
            completed_at=session.completed_at,
            duration_ms=session.duration_ms,
            node_executions=[
                NodeExecutionItemDTO(
                    id=str(e.id),
                    node_type=e.node_type,
                    status=e.status,
                    result_data=e.result_data,
                    narrative_report=e.narrative_report,
                    error_type=e.error_type,
                    error_message=e.error_message,
                    started_at=e.started_at,
                    completed_at=e.completed_at,
                    duration_ms=e.duration_ms,
                )
                for e in executions
            ],
        )
