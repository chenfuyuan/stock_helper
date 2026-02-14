"""
研究会话领域实体。

表示一次完整的研究流水线执行，含状态转换：running → completed / partial / failed。
"""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ResearchSession(BaseModel):
    """研究会话实体，用于持久化与状态治理。"""

    id: UUID
    symbol: str
    status: Literal["running", "completed", "partial", "failed"] = "running"
    selected_experts: list[str] = Field(default_factory=list)
    options: dict[str, Any] = Field(default_factory=dict)
    trigger_source: str = "api"
    created_at: datetime
    completed_at: datetime | None = None
    duration_ms: int | None = None
    retry_count: int = 0
    parent_session_id: UUID | None = None

    def complete(self, completed_at: datetime, duration_ms: int) -> None:
        """全部节点成功完成时调用，更新为 completed。"""
        self.status = "completed"
        self.completed_at = completed_at
        self.duration_ms = duration_ms

    def fail(self, completed_at: datetime, duration_ms: int) -> None:
        """全部节点失败时调用，更新为 failed。"""
        self.status = "failed"
        self.completed_at = completed_at
        self.duration_ms = duration_ms

    def mark_partial(self, completed_at: datetime, duration_ms: int) -> None:
        """部分节点成功、部分失败时调用，更新为 partial。"""
        self.status = "partial"
        self.completed_at = completed_at
        self.duration_ms = duration_ms
