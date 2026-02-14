"""
历史会话查询响应 DTO：会话摘要、会话详情、LLM 调用项、外部 API 调用项。
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class SessionSummaryDTO(BaseModel):
    """会话列表项（摘要）。"""

    id: str = Field(..., description="会话 ID")
    symbol: str = Field(..., description="股票代码")
    status: str = Field(..., description="running / completed / partial / failed")
    created_at: datetime = Field(..., description="创建时间")
    completed_at: datetime | None = Field(None, description="完成时间")
    duration_ms: int | None = Field(None, description="总耗时（毫秒）")


class NodeExecutionItemDTO(BaseModel):
    """单条节点执行记录（用于会话详情）。"""

    id: str = Field(..., description="记录 ID")
    node_type: str = Field(..., description="节点类型")
    status: str = Field(..., description="success / failed / skipped")
    result_data: dict[str, Any] | None = Field(None, description="结构化结果")
    narrative_report: str | None = Field(None, description="叙述性报告")
    error_type: str | None = Field(None, description="异常类名")
    error_message: str | None = Field(None, description="错误详情")
    started_at: datetime = Field(..., description="开始时间")
    completed_at: datetime | None = Field(None, description="结束时间")
    duration_ms: int | None = Field(None, description="节点耗时（毫秒）")


class SessionDetailDTO(BaseModel):
    """会话详情（含节点执行列表）。"""

    id: str = Field(..., description="会话 ID")
    symbol: str = Field(..., description="股票代码")
    status: str = Field(..., description="running / completed / partial / failed")
    selected_experts: list[str] = Field(default_factory=list, description="选中的专家列表")
    options: dict[str, Any] = Field(default_factory=dict, description="执行选项")
    trigger_source: str = Field("api", description="触发来源")
    created_at: datetime = Field(..., description="创建时间")
    completed_at: datetime | None = Field(None, description="完成时间")
    duration_ms: int | None = Field(None, description="总耗时（毫秒）")
    node_executions: list[NodeExecutionItemDTO] = Field(
        default_factory=list,
        description="节点执行记录列表，按 started_at 升序",
    )


class LLMCallItemDTO(BaseModel):
    """单条 LLM 调用日志（列表项）。"""

    id: str = Field(..., description="记录 ID")
    caller_module: str = Field("", description="调用方模块")
    caller_agent: str | None = Field(None, description="调用方 Agent")
    model_name: str = Field(..., description="模型名称")
    vendor: str = Field(..., description="供应商")
    prompt_tokens: int | None = Field(None, description="prompt token 数")
    completion_tokens: int | None = Field(None, description="completion token 数")
    total_tokens: int | None = Field(None, description="总 token 数")
    latency_ms: int = Field(..., description="调用耗时（毫秒）")
    status: str = Field(..., description="success / failed")
    created_at: datetime = Field(..., description="记录时间")


class ExternalAPICallItemDTO(BaseModel):
    """单条外部 API 调用日志（列表项）。"""

    id: str = Field(..., description="记录 ID")
    service_name: str = Field(..., description="服务名")
    operation: str = Field(..., description="操作")
    status_code: int | None = Field(None, description="HTTP 状态码")
    latency_ms: int = Field(..., description="调用耗时（毫秒）")
    status: str = Field(..., description="success / failed")
    created_at: datetime = Field(..., description="记录时间")
