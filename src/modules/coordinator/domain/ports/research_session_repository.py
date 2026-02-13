"""
研究会话与节点执行持久化 Port。

由 Coordinator 编排层使用，实现位于 infrastructure/persistence。
"""
from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from src.modules.coordinator.domain.model.node_execution import NodeExecution
from src.modules.coordinator.domain.model.research_session import ResearchSession


class IResearchSessionRepository(ABC):
    """研究会话与节点执行仓储抽象。"""

    @abstractmethod
    async def save_session(self, session: ResearchSession) -> None:
        """持久化新会话（创建）。"""
        ...

    @abstractmethod
    async def update_session(self, session: ResearchSession) -> None:
        """更新会话（状态、completed_at、duration_ms）。"""
        ...

    @abstractmethod
    async def save_node_execution(self, execution: NodeExecution) -> None:
        """持久化单条节点执行记录。"""
        ...

    @abstractmethod
    async def get_session_by_id(self, session_id: UUID) -> ResearchSession | None:
        """按 ID 查询会话，不存在返回 None。"""
        ...

    @abstractmethod
    async def list_sessions(
        self,
        *,
        symbol: str | None = None,
        created_after: datetime | None = None,
        created_before: datetime | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> list[ResearchSession]:
        """分页查询会话列表，支持按 symbol、时间范围筛选。"""
        ...

    @abstractmethod
    async def get_node_executions_by_session(self, session_id: UUID) -> list[NodeExecution]:
        """查询某会话下的全部节点执行记录，按 started_at 排序。"""
        ...
