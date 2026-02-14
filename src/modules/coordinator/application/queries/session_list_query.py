"""
会话列表查询用例：支持 symbol、时间范围、分页。
"""

from datetime import datetime

from src.modules.coordinator.application.dtos.session_dtos import (
    SessionSummaryDTO,
)
from src.modules.coordinator.domain.ports.research_session_repository import (
    IResearchSessionRepository,
)


class SessionListQuery:
    """查询研究会话列表，支持按 symbol、时间范围筛选与分页。"""

    def __init__(self, session_repo: IResearchSessionRepository) -> None:
        self._repo = session_repo

    async def execute(
        self,
        *,
        symbol: str | None = None,
        created_after: datetime | None = None,
        created_before: datetime | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> list[SessionSummaryDTO]:
        """返回符合条件的会话摘要列表，按 created_at 降序。"""
        sessions = await self._repo.list_sessions(
            symbol=symbol,
            created_after=created_after,
            created_before=created_before,
            skip=skip,
            limit=limit,
        )
        return [
            SessionSummaryDTO(
                id=str(s.id),
                symbol=s.symbol,
                status=s.status,
                created_at=s.created_at,
                completed_at=s.completed_at,
                duration_ms=s.duration_ms,
            )
            for s in sessions
        ]
