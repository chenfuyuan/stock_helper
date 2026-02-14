"""
研究编排 DTO：请求、结果、专家单项结果。

作为 Port 的入参/出参，定义在 domain/dtos 以符合 tech-standards（Port 使用的 DTO 在 domain/dtos）。
Application 和 Presentation 层从 domain 导入消费。
"""
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel

from src.modules.coordinator.domain.model.enums import ExpertType


class ResearchRequest(BaseModel):
    """研究编排请求 DTO。"""

    symbol: str
    experts: list[ExpertType]
    options: dict[str, dict[str, Any]] = {}
    skip_debate: bool = False
    pre_populated_results: dict[str, Any] | None = None  # 重试时传入已成功专家的 result_data
    parent_session_id: UUID | None = None  # 重试时关联的源 session ID
    retry_count: int = 0  # 重试计数，首次执行为 0


class ExpertResultItem(BaseModel):
    """单个专家的执行结果项。"""

    expert_type: ExpertType
    status: Literal["success", "failed"]
    data: dict[str, Any] | None = None
    error: str | None = None


class ResearchResult(BaseModel):
    """研究编排汇总结果 DTO。"""

    symbol: str
    overall_status: Literal["completed", "partial", "failed"]
    expert_results: list[ExpertResultItem]
    debate_outcome: dict[str, Any] | None = None  # 辩论结果，skip_debate 或失败时为 None
    verdict: dict[str, Any] | None = None  # 裁决结果，skip_debate、辩论失败或裁决失败时为 None
    session_id: str = ""  # 研究会话 ID，用于历史查询与审计关联；未启用持久化时为空
    retry_count: int = 0  # 重试计数，首次执行为 0，每次重试递增 1
