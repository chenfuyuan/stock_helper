"""
外部 API 调用日志持久化 Port。

由 llm_platform（如 WebSearchService）写入，由 Coordinator 历史查询通过查询服务读取。
"""

from abc import ABC, abstractmethod
from uuid import UUID

from src.shared.domain.dtos.external_api_call_log_dtos import (
    ExternalAPICallLog,
)


class IExternalAPICallLogRepository(ABC):
    """外部 API 调用日志仓储抽象。"""

    @abstractmethod
    async def save(self, log: ExternalAPICallLog) -> None:
        """持久化单条调用日志。"""
        ...

    @abstractmethod
    async def get_by_session_id(self, session_id: UUID) -> list[ExternalAPICallLog]:
        """按 session_id 查询调用日志，按 created_at 升序。"""
        ...
