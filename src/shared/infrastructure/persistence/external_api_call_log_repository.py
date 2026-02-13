"""
外部 API 调用日志 PostgreSQL 仓储实现。
"""
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.domain.dtos.external_api_call_log_dtos import ExternalAPICallLog
from src.shared.domain.ports.external_api_call_log_repository import IExternalAPICallLogRepository
from src.shared.infrastructure.persistence.external_api_call_log_model import ExternalAPICallLogModel


def _dto_to_model(d: ExternalAPICallLog) -> ExternalAPICallLogModel:
    return ExternalAPICallLogModel(
        id=d.id,
        session_id=d.session_id,
        service_name=d.service_name,
        operation=d.operation,
        request_params=d.request_params,
        response_data=d.response_data,
        status_code=d.status_code,
        latency_ms=d.latency_ms,
        status=d.status,
        error_message=d.error_message,
        created_at=d.created_at,
    )


def _model_to_dto(m: ExternalAPICallLogModel) -> ExternalAPICallLog:
    return ExternalAPICallLog(
        id=m.id,
        session_id=m.session_id,
        service_name=m.service_name,
        operation=m.operation,
        request_params=m.request_params or {},
        response_data=m.response_data,
        status_code=m.status_code,
        latency_ms=m.latency_ms,
        status=m.status,
        error_message=m.error_message,
        created_at=m.created_at,
    )


class PgExternalAPICallLogRepository(IExternalAPICallLogRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, log: ExternalAPICallLog) -> None:
        model = _dto_to_model(log)
        self._session.add(model)
        await self._session.commit()

    async def get_by_session_id(self, session_id: UUID) -> list[ExternalAPICallLog]:
        result = await self._session.execute(
            select(ExternalAPICallLogModel)
            .where(ExternalAPICallLogModel.session_id == session_id)
            .order_by(ExternalAPICallLogModel.created_at.asc())
        )
        models = result.scalars().all()
        return [_model_to_dto(m) for m in models]
