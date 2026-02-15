"""调度器领域 DTO 定义

定义调度器相关的数据传输对象，用于 Port 接口的输入输出。
所有 DTO 都使用 Pydantic 进行数据校验和序列化。
"""

from datetime import datetime
from typing import Dict, Any, Optional
from enum import Enum
from pydantic import BaseModel, Field, validator


class JobStatus(str, Enum):
    """任务执行状态枚举"""
    PENDING = "pending"      # 等待执行
    RUNNING = "running"      # 正在执行
    SUCCESS = "success"      # 执行成功
    FAILED = "failed"        # 执行失败
    CANCELLED = "cancelled"  # 已取消


class JobConfigDTO(BaseModel):
    """任务配置 DTO
    
    包含任务的基本配置信息，用于调度器注册任务。
    """
    job_id: str = Field(..., description="任务唯一标识符", min_length=1)
    job_name: str = Field(..., description="任务名称", min_length=1)
    cron_expression: str = Field(..., description="Cron 表达式")
    timezone: str = Field(default="UTC", description="时区")
    enabled: bool = Field(default=True, description="是否启用")
    job_kwargs: Dict[str, Any] = Field(default_factory=dict, description="任务参数")

    @validator('cron_expression')
    def validate_cron_expression(cls, v):
        """验证 Cron 表达式格式"""
        # 简单的 cron 表达式验证（5 位或 6 位）
        parts = v.split()
        if len(parts) not in (5, 6):
            raise ValueError("Cron 表达式必须包含 5 或 6 个部分")
        
        # 验证每部分都是有效的 cron 值
        for part in parts:
            if part not in ('*', '?') and not all(c.isdigit() or c in '*/-' for c in part):
                raise ValueError(f"无效的 cron 表达式部分: {part}")
        
        return v

    @validator('timezone')
    def validate_timezone(cls, v):
        """验证时区"""
        # 简单的时区验证（实际项目中可能需要更严格的验证）
        valid_timezones = ['UTC', 'Asia/Shanghai', 'Asia/Tokyo', 'America/New_York']
        if v not in valid_timezones:
            raise ValueError(f"不支持的时区: {v}")
        return v


class JobStatusDTO(BaseModel):
    """任务状态 DTO
    
    包含任务的当前运行状态信息。
    """
    job_id: str = Field(..., description="任务唯一标识符")
    job_name: str = Field(..., description="任务名称")
    is_running: bool = Field(default=False, description="是否正在运行")
    next_run_time: Optional[datetime] = Field(None, description="下次运行时间")
    trigger_description: Optional[str] = Field(None, description="触发器描述")
    job_kwargs: Dict[str, Any] = Field(default_factory=dict, description="任务参数")

    @validator('next_run_time')
    def validate_next_run_time(cls, v):
        """验证下次运行时间"""
        if v is not None and v < datetime.now():
            raise ValueError("下次运行时间不能是过去的时间")
        return v


class JobExecutionDTO(BaseModel):
    """任务执行记录 DTO
    
    记录任务执行的历史信息。
    """
    job_id: str = Field(..., description="任务唯一标识符")
    started_at: datetime = Field(..., description="开始时间")
    finished_at: Optional[datetime] = Field(None, description="结束时间")
    status: JobStatus = Field(..., description="执行状态")
    error_message: Optional[str] = Field(None, description="错误信息")
    duration_ms: Optional[int] = Field(None, description="执行耗时（毫秒）", ge=0)

    @validator('finished_at')
    def validate_finished_at(cls, v, values):
        """验证结束时间"""
        if v is not None and 'started_at' in values and v < values['started_at']:
            raise ValueError("结束时间不能早于开始时间")
        return v

    @validator('duration_ms')
    def validate_duration_ms(cls, v, values):
        """验证持续时间"""
        if v is not None and v < 0:
            raise ValueError("持续时间不能为负数")
        return v

    @validator('error_message')
    def validate_error_message(cls, v, values):
        """验证错误信息"""
        if v is not None and 'status' in values and values['status'] == JobStatus.SUCCESS:
            raise ValueError("成功状态不能有错误信息")
        return v


class SchedulerConfigDTO(BaseModel):
    """调度器配置 DTO
    
    调度器实例的配置信息。
    """
    timezone: str = Field(default="UTC", description="默认时区")
    max_workers: int = Field(default=5, description="最大工作线程数", ge=1, le=20)
    job_defaults: Dict[str, Any] = Field(default_factory=dict, description="任务默认配置")

    @validator('timezone')
    def validate_timezone(cls, v):
        """验证时区"""
        valid_timezones = ['UTC', 'Asia/Shanghai', 'Asia/Tokyo', 'America/New_York']
        if v not in valid_timezones:
            raise ValueError(f"不支持的时区: {v}")
        return v

    @validator('job_defaults')
    def validate_job_defaults(cls, v):
        """验证任务默认配置"""
        # 验证常见的配置项
        supported_keys = {'coalesce', 'max_instances', 'misfire_grace_time', 'timezone'}
        for key in v.keys():
            if key not in supported_keys:
                raise ValueError(f"不支持的任务配置项: {key}")
        return v
