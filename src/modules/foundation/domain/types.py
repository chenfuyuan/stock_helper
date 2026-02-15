"""调度器公共类型别名定义

定义调度器相关的类型别名，提供类型安全和代码可读性。
这些类型别名在 Port 接口、DTO 和服务实现中广泛使用。
"""

from typing import Dict, Any, Optional, Callable, Union
from datetime import datetime

# ==================== 基础类型别名 ====================

# 任务标识符类型
JobId = str

# 任务名称类型
JobName = str

# Cron 表达式类型
CronExpression = str

# 时区类型
Timezone = str

# 任务函数类型
JobFunction = Callable

# 任务参数类型
JobParameters = Dict[str, Any]

# ==================== 状态类型别名 ====================

# 任务状态类型
JobStatus = str

# 执行状态类型
ExecutionStatus = str

# ==================== 配置类型别名 ====================

# 调度器配置类型
SchedulerConfig = Dict[str, Any]

# 任务注册表类型
JobRegistry = Dict[str, JobFunction]

# ==================== 时间类型别名 ====================

# 时间戳类型
Timestamp = datetime

# 毫秒类型
Milliseconds = int

# ==================== 复合类型别名 ====================

# 可选任务参数类型
OptionalJobParameters = Optional[JobParameters]

# 可选时间戳类型
OptionalTimestamp = Optional[Timestamp]

# 可选毫秒类型
OptionalMilliseconds = Optional[Milliseconds]

# 任务状态详情类型
JobStatusDetails = Dict[str, Any]

# 执行日志类型
ExecutionLog = Dict[str, Any]

# ==================== 函数签名类型别名 ====================

# 数据库会话工厂类型
SessionFactory = Callable

# 异步任务函数类型
AsyncJobFunction = Callable[..., Any]

# 任务执行回调类型
JobExecutionCallback = Callable[[str, ExecutionStatus, Optional[Exception]], None]

# ==================== 验证相关类型别名 ====================

# 验证结果类型
ValidationResult = Dict[str, Union[bool, str]]

# 错误详情类型
ErrorDetails = Dict[str, Any]

# ==================== 配置选项类型别名 ====================

# 调度器启动选项类型
SchedulerStartupOptions = Dict[str, Any]

# 任务调度选项类型
JobScheduleOptions = Dict[str, Any]

# ==================== 常量定义 ====================

# 常用的任务状态值
class JobStatusValues:
    """任务状态常量"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"

# 常用的执行状态值
class ExecutionStatusValues:
    """执行状态常量"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"

# 常用的时区值
class TimezoneValues:
    """时区常量"""
    UTC = "UTC"
    ASIA_SHANGHAI = "Asia/Shanghai"
    ASIA_TOKYO = "Asia/Tokyo"
    AMERICA_NEW_YORK = "America/New_York"
    EUROPE_LONDON = "Europe/London"

# 常用的 Cron 表达式模板
class CronTemplates:
    """Cron 表达式模板"""
    DAILY_MIDNIGHT = "0 0 * * *"
    HOURLY = "0 * * * *"
    EVERY_15_MINUTES = "*/15 * * * *"
    WEEKLY_MONDAY_9AM = "0 9 * * 1"
    MONTHLY_1ST = "0 0 1 * *"
    WORKDAYS_9AM = "0 9 * * 1-5"
