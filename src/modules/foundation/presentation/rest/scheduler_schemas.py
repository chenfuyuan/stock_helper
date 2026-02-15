"""Scheduler REST API Schemas

Pydantic models for scheduler-related HTTP requests and responses.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class JobDetail(BaseModel):
    """任务详情 DTO"""

    id: str = Field(..., description="任务ID")
    name: str = Field(..., description="任务名称")
    next_run_time: Optional[datetime] = Field(None, description="下次运行时间")
    trigger: str = Field(..., description="触发器描述")
    kwargs: Dict[str, Any] = Field(default_factory=dict, description="任务参数")


class SchedulerStatusResponse(BaseModel):
    """调度器状态响应 DTO"""

    is_running: bool = Field(..., description="调度器是否运行中")
    jobs: List[JobDetail] = Field(..., description="当前已调度的任务列表")
    available_jobs: List[str] = Field(..., description="系统支持的可注册任务列表")


class ExecutionLogDetail(BaseModel):
    """执行日志详情 DTO"""

    job_id: str = Field(..., description="任务标识")
    started_at: datetime = Field(..., description="开始时间")
    finished_at: Optional[datetime] = Field(None, description="结束时间")
    status: str = Field(..., description="执行状态")
    error_message: Optional[str] = Field(None, description="错误信息")
    duration_ms: Optional[int] = Field(None, description="执行耗时（毫秒）")
