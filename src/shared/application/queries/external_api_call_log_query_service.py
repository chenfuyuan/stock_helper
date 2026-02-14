"""
按 session_id 查询外部 API 调用日志的查询服务。

供 Coordinator 历史查询 API 等调用。
"""

from uuid import UUID

from src.shared.domain.dtos.external_api_call_log_dtos import (
    ExternalAPICallLog,
)
from src.shared.domain.ports.external_api_call_log_repository import (
    IExternalAPICallLogRepository,
)


class ExternalAPICallLogQueryService:
    """按会话查询外部 API 调用日志。"""

    def __init__(self, repository: IExternalAPICallLogRepository) -> None:
        self._repository = repository

    async def get_by_session_id(
        self, session_id: UUID
    ) -> list[ExternalAPICallLog]:
        """返回该 session 下所有外部 API 调用日志，按 created_at 升序。"""
        return await self._repository.get_by_session_id(session_id)
