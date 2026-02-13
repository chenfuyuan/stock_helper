"""
LLM 调用日志持久化 Port。
"""
from abc import ABC, abstractmethod
from uuid import UUID

from src.modules.llm_platform.domain.dtos.llm_call_log_dtos import LLMCallLog


class ILLMCallLogRepository(ABC):
    """LLM 调用日志仓储抽象。"""

    @abstractmethod
    async def save(self, log: LLMCallLog) -> None:
        """持久化单条调用日志。"""
        ...

    @abstractmethod
    async def get_by_session_id(self, session_id: UUID) -> list[LLMCallLog]:
        """按 session_id 查询调用日志，按 created_at 升序。"""
        ...
