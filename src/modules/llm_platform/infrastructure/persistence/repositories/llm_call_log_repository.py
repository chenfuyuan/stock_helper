"""
LLM 调用日志 PostgreSQL 仓储实现。
"""
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.llm_platform.domain.dtos.llm_call_log_dtos import LLMCallLog
from src.modules.llm_platform.domain.ports.llm_call_log_repository import ILLMCallLogRepository
from src.modules.llm_platform.infrastructure.persistence.models.llm_call_log_model import LLMCallLogModel


def _dto_to_model(d: LLMCallLog) -> LLMCallLogModel:
    return LLMCallLogModel(
        id=d.id,
        session_id=d.session_id,
        caller_module=d.caller_module,
        caller_agent=d.caller_agent,
        model_name=d.model_name,
        vendor=d.vendor,
        prompt_text=d.prompt_text,
        system_message=d.system_message,
        completion_text=d.completion_text,
        prompt_tokens=d.prompt_tokens,
        completion_tokens=d.completion_tokens,
        total_tokens=d.total_tokens,
        temperature=d.temperature,
        latency_ms=d.latency_ms,
        status=d.status,
        error_message=d.error_message,
        created_at=d.created_at,
    )


def _model_to_dto(m: LLMCallLogModel) -> LLMCallLog:
    return LLMCallLog(
        id=m.id,
        session_id=m.session_id,
        caller_module=m.caller_module,
        caller_agent=m.caller_agent,
        model_name=m.model_name,
        vendor=m.vendor,
        prompt_text=m.prompt_text,
        system_message=m.system_message,
        completion_text=m.completion_text,
        prompt_tokens=m.prompt_tokens,
        completion_tokens=m.completion_tokens,
        total_tokens=m.total_tokens,
        temperature=m.temperature,
        latency_ms=m.latency_ms,
        status=m.status,
        error_message=m.error_message,
        created_at=m.created_at,
    )


class PgLLMCallLogRepository(ILLMCallLogRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, log: LLMCallLog) -> None:
        model = _dto_to_model(log)
        self._session.add(model)
        await self._session.commit()

    async def get_by_session_id(self, session_id: UUID) -> list[LLMCallLog]:
        result = await self._session.execute(
            select(LLMCallLogModel)
            .where(LLMCallLogModel.session_id == session_id)
            .order_by(LLMCallLogModel.created_at.asc())
        )
        models = result.scalars().all()
        return [_model_to_dto(m) for m in models]
