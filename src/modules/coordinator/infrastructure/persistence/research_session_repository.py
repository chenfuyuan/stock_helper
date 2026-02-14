"""
研究会话与节点执行 PostgreSQL 仓储实现。
"""
from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.coordinator.domain.model.node_execution import NodeExecution
from src.modules.coordinator.domain.model.research_session import ResearchSession
from src.modules.coordinator.domain.ports.research_session_repository import IResearchSessionRepository
from src.modules.coordinator.infrastructure.persistence.node_execution_model import NodeExecutionModel
from src.modules.coordinator.infrastructure.persistence.research_session_model import ResearchSessionModel


def _session_model_to_entity(m: ResearchSessionModel) -> ResearchSession:
    """ORM 转研究会话实体。"""
    return ResearchSession(
        id=m.id,
        symbol=m.symbol,
        status=m.status,
        selected_experts=list(m.selected_experts) if m.selected_experts else [],
        options=dict(m.options) if m.options else {},
        trigger_source=m.trigger_source or "api",
        created_at=m.created_at,
        completed_at=m.completed_at,
        duration_ms=m.duration_ms,
        retry_count=m.retry_count or 0,
        parent_session_id=m.parent_session_id,
    )


def _session_entity_to_model(s: ResearchSession) -> ResearchSessionModel:
    """研究会话实体转 ORM。"""
    return ResearchSessionModel(
        id=s.id,
        symbol=s.symbol,
        status=s.status,
        selected_experts=s.selected_experts,
        options=s.options,
        trigger_source=s.trigger_source,
        created_at=s.created_at,
        completed_at=s.completed_at,
        duration_ms=s.duration_ms,
        retry_count=s.retry_count,
        parent_session_id=s.parent_session_id,
    )


def _execution_model_to_entity(m: NodeExecutionModel) -> NodeExecution:
    """ORM 转节点执行实体。"""
    return NodeExecution(
        id=m.id,
        session_id=m.session_id,
        node_type=m.node_type,
        status=m.status,
        result_data=dict(m.result_data) if m.result_data else None,
        narrative_report=m.narrative_report,
        error_type=m.error_type,
        error_message=m.error_message,
        started_at=m.started_at,
        completed_at=m.completed_at,
        duration_ms=m.duration_ms,
    )


def _execution_entity_to_model(e: NodeExecution) -> NodeExecutionModel:
    """节点执行实体转 ORM。"""
    return NodeExecutionModel(
        id=e.id,
        session_id=e.session_id,
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


class PgResearchSessionRepository(IResearchSessionRepository):
    """研究会话与节点执行的 PostgreSQL 实现。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save_session(self, session: ResearchSession) -> None:
        model = _session_entity_to_model(session)
        self._session.add(model)
        await self._session.commit()

    async def update_session(self, session: ResearchSession) -> None:
        await self._session.execute(
            update(ResearchSessionModel)
            .where(ResearchSessionModel.id == session.id)
            .values(
                status=session.status,
                completed_at=session.completed_at,
                duration_ms=session.duration_ms,
            )
        )
        await self._session.commit()

    async def save_node_execution(self, execution: NodeExecution) -> None:
        model = _execution_entity_to_model(execution)
        self._session.add(model)
        await self._session.commit()

    async def get_session_by_id(self, session_id: UUID) -> ResearchSession | None:
        result = await self._session.execute(
            select(ResearchSessionModel).where(ResearchSessionModel.id == session_id)
        )
        model = result.scalar_one_or_none()
        return _session_model_to_entity(model) if model else None

    async def list_sessions(
        self,
        *,
        symbol: str | None = None,
        created_after: datetime | None = None,
        created_before: datetime | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> list[ResearchSession]:
        q = select(ResearchSessionModel)
        if symbol is not None:
            q = q.where(ResearchSessionModel.symbol == symbol)
        if created_after is not None:
            q = q.where(ResearchSessionModel.created_at >= created_after)
        if created_before is not None:
            q = q.where(ResearchSessionModel.created_at <= created_before)
        q = q.order_by(ResearchSessionModel.created_at.desc()).offset(skip).limit(limit)
        result = await self._session.execute(q)
        models = result.scalars().all()
        return [_session_model_to_entity(m) for m in models]

    async def get_node_executions_by_session(self, session_id: UUID) -> list[NodeExecution]:
        result = await self._session.execute(
            select(NodeExecutionModel)
            .where(NodeExecutionModel.session_id == session_id)
            .order_by(NodeExecutionModel.started_at.asc())
        )
        models = result.scalars().all()
        return [_execution_model_to_entity(m) for m in models]
