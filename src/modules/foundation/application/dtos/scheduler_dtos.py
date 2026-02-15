"""调度器应用层 DTO 定义

定义应用层对外暴露的 DTO，用于 API 响应和跨模块通信。
这些 DTO 专门为应用层设计，不暴露领域实体。
"""

from datetime import datetime
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field, validator


class SchedulerRequestDTO(BaseModel):
    """调度器请求 DTO
    
    用于接收调度器相关的操作请求。
    """
    action: str = Field(..., description="操作动作：start, stop, restart, status")
    config: Optional[Dict[str, Any]] = Field(None, description="调度器配置参数")

    @validator('action')
    def validate_action(cls, v):
        """验证操作动作"""
        valid_actions = ['start', 'stop', 'restart', 'status', 'health']
        if v not in valid_actions:
            raise ValueError(f"无效的动作: {v}，支持的动作: {valid_actions}")
        return v

    @validator('action')
    def validate_action_not_empty(cls, v):
        """验证动作不为空"""
        if not v or not v.strip():
            raise ValueError("动作不能为空")
        return v.strip()


class SchedulerResponseDTO(BaseModel):
    """调度器响应 DTO
    
    用于返回调度器操作的结果。
    """
    success: bool = Field(..., description="操作是否成功")
    message: str = Field(..., description="操作结果消息")
    data: Optional[Dict[str, Any]] = Field(None, description="响应数据")
    error_code: Optional[str] = Field(None, description="错误代码")
    errors: Optional[List[str]] = Field(None, description="错误详情列表")
    timestamp: datetime = Field(default_factory=datetime.now, description="响应时间戳")


class JobScheduleRequestDTO(BaseModel):
    """任务调度请求 DTO
    
    用于创建或更新任务调度配置。
    """
    job_id: str = Field(..., description="任务唯一标识符", min_length=1)
    job_name: str = Field(..., description="任务名称", min_length=1)
    cron_expression: str = Field(..., description="Cron 表达式")
    timezone: str = Field(default="UTC", description="时区")
    enabled: bool = Field(default=True, description="是否启用")
    job_kwargs: Dict[str, Any] = Field(default_factory=dict, description="任务参数")

    @validator('job_id')
    def validate_job_id_not_empty(cls, v):
        """验证任务ID不为空"""
        if not v or not v.strip():
            raise ValueError("任务ID不能为空")
        return v.strip()

    @validator('cron_expression')
    def validate_cron_expression(cls, v):
        """验证 Cron 表达式格式"""
        parts = v.split()
        if len(parts) not in (5, 6):
            raise ValueError(f"无效的Cron表达式: {v}，必须包含 5 或 6 个部分")
        
        # 简单验证每部分格式
        for part in parts:
            if part not in ('*', '?') and not all(c.isdigit() or c in '*/-' for c in part):
                raise ValueError(f"无效的Cron表达式部分: {part}")
        
        return v

    @validator('timezone')
    def validate_timezone(cls, v):
        """验证时区"""
        valid_timezones = ['UTC', 'Asia/Shanghai', 'Asia/Tokyo', 'America/New_York']
        if v not in valid_timezones:
            raise ValueError(f"不支持的时区: {v}")
        return v


class JobScheduleResponseDTO(BaseModel):
    """任务调度响应 DTO
    
    用于返回任务调度操作的结果。
    """
    job_id: str = Field(..., description="任务ID")
    job_name: str = Field(..., description="任务名称")
    scheduled: bool = Field(..., description="是否调度成功")
    cron_expression: Optional[str] = Field(None, description="Cron 表达式")
    next_run_time: Optional[datetime] = Field(None, description="下次运行时间")
    message: str = Field(..., description="操作结果消息")
    error_code: Optional[str] = Field(None, description="错误代码")
    error_message: Optional[str] = Field(None, description="错误详情")
    timestamp: datetime = Field(default_factory=datetime.now, description="响应时间戳")


class JobExecutionRequestDTO(BaseModel):
    """任务执行请求 DTO
    
    用于手动触发、暂停、恢复或停止任务。
    """
    job_id: str = Field(..., description="任务ID", min_length=1)
    action: str = Field(..., description="执行动作：trigger, pause, resume, stop")
    parameters: Optional[Dict[str, Any]] = Field(None, description="执行参数")

    @validator('action')
    def validate_action(cls, v):
        """验证执行动作"""
        valid_actions = ['trigger', 'pause', 'resume', 'stop']
        if v not in valid_actions:
            raise ValueError(f"无效的执行动作: {v}，支持的动作: {valid_actions}")
        return v


class JobExecutionResponseDTO(BaseModel):
    """任务执行响应 DTO
    
    用于返回任务执行操作的结果。
    """
    job_id: str = Field(..., description="任务ID")
    action: str = Field(..., description="执行动作")
    success: bool = Field(..., description="执行是否成功")
    message: str = Field(..., description="执行结果消息")
    execution_id: Optional[str] = Field(None, description="执行ID")
    started_at: Optional[datetime] = Field(None, description="开始时间")
    finished_at: Optional[datetime] = Field(None, description="结束时间")
    duration_ms: Optional[int] = Field(None, description="执行耗时（毫秒）")
    error_code: Optional[str] = Field(None, description="错误代码")
    error_details: Optional[Dict[str, Any]] = Field(None, description="错误详情")
    timestamp: datetime = Field(default_factory=datetime.now, description="响应时间戳")

    @validator('duration_ms')
    def validate_duration_ms(cls, v):
        """验证持续时间"""
        if v is not None and v < 0:
            raise ValueError("持续时间不能为负数")
        return v


class SchedulerHealthDTO(BaseModel):
    """调度器健康状态 DTO
    
    用于返回调度器的健康状态信息。
    """
    status: str = Field(..., description="健康状态")
    uptime_seconds: int = Field(..., description="运行时间（秒）", ge=0)
    running_jobs: int = Field(..., description="正在运行的任务数", ge=0)
    total_jobs: int = Field(..., description="总任务数", ge=0)
    last_execution_time: Optional[datetime] = Field(None, description="最后执行时间")
    next_execution_time: Optional[datetime] = Field(None, description="下次执行时间")
    memory_usage_mb: Optional[float] = Field(None, description="内存使用量（MB）", ge=0)
    cpu_usage_percent: Optional[float] = Field(None, description="CPU使用率（百分比）", ge=0, le=100)
    error_message: Optional[str] = Field(None, description="错误信息")
    timestamp: datetime = Field(default_factory=datetime.now, description="状态时间戳")

    @validator('status')
    def validate_status(cls, v):
        """验证健康状态"""
        valid_statuses = ['healthy', 'unhealthy', 'degraded', 'starting', 'stopping']
        if v not in valid_statuses:
            raise ValueError(f"无效的健康状态: {v}，支持的状态: {valid_statuses}")
        return v


class JobListResponseDTO(BaseModel):
    """任务列表响应 DTO
    
    用于返回任务列表信息。
    """
    jobs: List[Dict[str, Any]] = Field(..., description="任务列表")
    total_count: int = Field(..., description="任务总数", ge=0)
    running_count: int = Field(..., description="正在运行的任务数", ge=0)
    timestamp: datetime = Field(default_factory=datetime.now, description="响应时间戳")


class JobDetailResponseDTO(BaseModel):
    """任务详情响应 DTO
    
    用于返回单个任务的详细信息。
    """
    job_id: str = Field(..., description="任务ID")
    job_name: str = Field(..., description="任务名称")
    is_running: bool = Field(..., description="是否正在运行")
    cron_expression: Optional[str] = Field(None, description="Cron 表达式")
    timezone: Optional[str] = Field(None, description="时区")
    next_run_time: Optional[datetime] = Field(None, description="下次运行时间")
    last_run_time: Optional[datetime] = Field(None, description="上次运行时间")
    last_execution_status: Optional[str] = Field(None, description="上次执行状态")
    execution_count: int = Field(..., description="执行次数", ge=0)
    success_count: int = Field(..., description="成功次数", ge=0)
    failure_count: int = Field(..., description="失败次数", ge=0)
    average_duration_ms: Optional[float] = Field(None, description="平均执行时间（毫秒）", ge=0)
    enabled: bool = Field(..., description="是否启用")
    job_kwargs: Dict[str, Any] = Field(default_factory=dict, description="任务参数")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    timestamp: datetime = Field(default_factory=datetime.now, description="响应时间戳")


class ExecutionHistoryResponseDTO(BaseModel):
    """执行历史响应 DTO
    
    用于返回任务执行历史记录。
    """
    job_id: str = Field(..., description="任务ID")
    executions: List[Dict[str, Any]] = Field(..., description="执行记录列表")
    total_count: int = Field(..., description="总记录数", ge=0)
    success_count: int = Field(..., description="成功次数", ge=0)
    failure_count: int = Field(..., description="失败次数", ge=0)
    average_duration_ms: Optional[float] = Field(None, description="平均执行时间（毫秒）", ge=0)
    timestamp: datetime = Field(default_factory=datetime.now, description="响应时间戳")


class SchedulerConfigResponseDTO(BaseModel):
    """调度器配置响应 DTO
    
    用于返回调度器配置信息。
    """
    timezone: str = Field(..., description="默认时区")
    max_workers: int = Field(..., description="最大工作线程数", ge=1)
    job_defaults: Dict[str, Any] = Field(..., description="任务默认配置")
    features: Dict[str, bool] = Field(..., description="功能开关")
    version: str = Field(..., description="调度器版本")
    timestamp: datetime = Field(default_factory=datetime.now, description="响应时间戳")
