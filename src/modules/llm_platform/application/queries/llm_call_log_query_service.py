"""
按 session_id 查询 LLM 调用日志的查询服务。

供 Coordinator 历史查询 API 调用，不直接暴露给 REST。
"""

from uuid import UUID

from src.modules.llm_platform.domain.dtos.llm_call_log_dtos import LLMCallLog
from src.modules.llm_platform.domain.ports.llm_call_log_repository import (
    ILLMCallLogRepository,
)


class LLMCallLogQueryService:
    """按会话查询 LLM 调用日志。"""

    def __init__(self, repository: ILLMCallLogRepository) -> None:
        self._repository = repository

    async def get_by_session_id(self, session_id: UUID) -> list[LLMCallLog]:
        """返回该 session 下所有 LLM 调用日志，按 created_at 升序。"""
        return await self._repository.get_by_session_id(session_id)
