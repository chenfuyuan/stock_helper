"""
节点执行领域实体。

表示 LangGraph 中单个节点（专家/debate/judge）的一次执行快照，含成功/失败记录。
"""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel


class NodeExecution(BaseModel):
    """节点执行记录实体。"""

    id: UUID
    session_id: UUID
    node_type: str  # technical_analyst / financial_auditor / ... / debate / judge
    status: Literal["success", "failed", "skipped"] = "success"
    result_data: dict[str, Any] | None = None
    narrative_report: str | None = None
    error_type: str | None = None
    error_message: str | None = None
    started_at: datetime
    completed_at: datetime | None = None
    duration_ms: int | None = None

    def mark_success(
        self,
        result_data: dict[str, Any],
        narrative_report: str,
        completed_at: datetime,
        duration_ms: int,
    ) -> None:
        """节点成功完成时调用，写入结果与报告。"""
        self.status = "success"
        self.result_data = result_data
        self.narrative_report = narrative_report or None
        self.completed_at = completed_at
        self.duration_ms = duration_ms
        self.error_type = None
        self.error_message = None

    def mark_failed(
        self,
        error_type: str,
        error_message: str,
        completed_at: datetime,
        duration_ms: int,
    ) -> None:
        """节点执行失败时调用，写入异常信息。"""
        self.status = "failed"
        self.error_type = error_type
        self.error_message = error_message
        self.completed_at = completed_at
        self.duration_ms = duration_ms
        self.result_data = None
        self.narrative_report = None
