"""
外部 API 调用日志 DTO，用于持久化与查询。
"""
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ExternalAPICallLog(BaseModel):
    """单次外部 API 调用的审计记录。"""

    id: UUID
    session_id: UUID | None = None
    service_name: str = ""
    operation: str = ""
    request_params: dict[str, Any] = Field(default_factory=dict)
    response_data: str | None = None
    status_code: int | None = None
    latency_ms: int = 0
    status: str = "success"  # success | failed
    error_message: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
