"""
LLM 调用审计 DTO：用于持久化与查询。
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class LLMCallLog(BaseModel):
    """单次 LLM 调用的审计记录。"""

    id: UUID
    session_id: UUID | None = None
    caller_module: str = ""
    caller_agent: str | None = None
    model_name: str
    vendor: str
    prompt_text: str = ""
    system_message: str | None = None
    completion_text: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    temperature: float = 0.0
    latency_ms: int = 0
    status: str = "success"  # success | failed
    error_message: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
