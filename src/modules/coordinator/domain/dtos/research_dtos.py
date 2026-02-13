"""
研究编排 DTO：请求、结果、专家单项结果。

作为 Port 的入参/出参，定义在 domain/dtos 以符合 tech-standards（Port 使用的 DTO 在 domain/dtos）。
Application 和 Presentation 层从 domain 导入消费。
"""
from typing import Any, Literal

from pydantic import BaseModel

from src.modules.coordinator.domain.model.enums import ExpertType


class ResearchRequest(BaseModel):
    """研究编排请求 DTO。"""

    symbol: str
    experts: list[ExpertType]
    options: dict[str, dict[str, Any]] = {}


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
