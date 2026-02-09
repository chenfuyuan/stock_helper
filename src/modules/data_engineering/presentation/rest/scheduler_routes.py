import pandas as pd
from fastapi import APIRouter, status, HTTPException, Body
from src.shared.dtos import BaseResponse
from src.shared.infrastructure.scheduler import SchedulerService
# Updated imports to point to the new location
from src.modules.data_engineering.presentation.jobs.sync_scheduler import (
    sync_history_daily_data_job,
    sync_daily_data_job,
    sync_finance_history_job,
    sync_incremental_finance_job
)
from pydantic import BaseModel, Field
from typing import Dict, Callable, Any, Optional, List
from datetime import datetime

router = APIRouter()

# 任务注册表：将任务 ID 映射到具体的任务函数
JOB_REGISTRY: Dict[str, Callable] = {
    "sync_daily_history": sync_history_daily_data_job,  # 历史数据同步（全量/断点续传）
    "sync_daily_by_date": sync_daily_data_job,          # 按日期同步（每日增量）- Renamed in new module
    "sync_history_finance": sync_finance_history_job,   # 历史财务数据同步
    "sync_incremental_finance": sync_incremental_finance_job, # 增量财务数据同步
}

class JobDetail(BaseModel):
    id: str = Field(..., description="任务ID")
    name: str = Field(..., description="任务名称")
    next_run_time: Optional[datetime] = Field(None, description="下次运行时间")
    trigger: str = Field(..., description="触发器描述")
    kwargs: Dict[str, Any] = Field(default_factory=dict, description="任务参数")

class SchedulerStatusResponse(BaseModel):
    is_running: bool = Field(..., description="调度器是否运行中")
    jobs: List[JobDetail] = Field(..., description="当前已调度的任务列表")
    available_jobs: List[str] = Field(..., description="系统支持的可注册任务列表")

@router.get(
    "/status",
    response_model=BaseResponse[SchedulerStatusResponse],
    summary="获取调度器状态"
)
async def get_status():
    scheduler = SchedulerService.get_scheduler()
    
    current_jobs = []
    for job in scheduler.get_jobs():
        current_jobs.append(JobDetail(
            id=job.id,
            name=job.name,
            next_run_time=job.next_run_time,
            trigger=str(job.trigger),
            kwargs=job.kwargs
        ))
    
    return BaseResponse(
        success=True,
        code="SCHEDULER_STATUS",
        message="获取状态成功",
        data=SchedulerStatusResponse(
            is_running=scheduler.running,
            jobs=current_jobs,
            available_jobs=list(JOB_REGISTRY.keys())
        )
    )

@router.post(
    "/jobs/{job_id}/start",
    response_model=BaseResponse[str],
    summary="启动指定定时任务 (Interval 模式)"
)
async def start_job(
    job_id: str, 
    interval_minutes: int = Body(..., embed=True, description="执行间隔(分钟)")
):
    """
    启动一个 Interval 模式的定时任务 (每隔 X 分钟执行一次)
    :param job_id: 任务ID (见 /status 返回的可选列表)
    :param interval_minutes: 间隔分钟数
    """
    if job_id not in JOB_REGISTRY:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found. Available jobs: {list(JOB_REGISTRY.keys())}"
        )
        
    scheduler = SchedulerService.get_scheduler()
    job_func = JOB_REGISTRY[job_id]
    
    # 如果任务已存在，先移除
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
        
    scheduler.add_job(
        job_func, 
        'interval', 
        minutes=interval_minutes, 
        id=job_id, 
        replace_existing=True
    )
    
    return BaseResponse(
        success=True,
        code="JOB_STARTED",
        message=f"已启动任务 '{job_id}'，每 {interval_minutes} 分钟执行一次",
        data="started"
    )

@router.post(
    "/jobs/{job_id}/schedule",
    response_model=BaseResponse[str],
    summary="启动指定定时任务 (Cron 模式)"
)
async def schedule_job(
    job_id: str,
    hour: int = Body(..., embed=True, description="执行小时 (0-23)"),
    minute: int = Body(..., embed=True, description="执行分钟 (0-59)")
):
    """
    启动一个 Cron 模式的定时任务 (每天固定时间执行)
    :param job_id: 任务ID (见 /status 返回的可选列表)
    :param hour: 小时
    :param minute: 分钟
    """
    if job_id not in JOB_REGISTRY:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found. Available jobs: {list(JOB_REGISTRY.keys())}"
        )

    scheduler = SchedulerService.get_scheduler()
    job_func = JOB_REGISTRY[job_id]
    
    # 如果任务已存在，先移除
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)

    scheduler.add_job(
        job_func,
        'cron',
        hour=hour,
        minute=minute,
        id=job_id,
        replace_existing=True
    )

    return BaseResponse(
        success=True,
        code="JOB_SCHEDULED",
        message=f"已调度任务 '{job_id}'，每天 {hour:02d}:{minute:02d} 执行",
        data="scheduled"
    )

@router.post(
    "/jobs/{job_id}/trigger",
    response_model=BaseResponse[str],
    summary="立即触发一次任务"
)
async def trigger_job(
    job_id: str,
    params: Optional[Dict[str, Any]] = Body(None, description="任务参数")
):
    """
    立即异步执行一次任务
    """
    if job_id not in JOB_REGISTRY:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found. Available jobs: {list(JOB_REGISTRY.keys())}"
        )

    scheduler = SchedulerService.get_scheduler()
    job_func = JOB_REGISTRY[job_id]
    
    # 使用 kwargs 传递参数
    kwargs = params or {}
    
    # 立即提交到线程池/协程池执行，不影响调度器
    # 注意：APScheduler 的 add_job 如果不指定 trigger，默认为 'date' 且 run_date 为当前时间
    scheduler.add_job(
        job_func,
        kwargs=kwargs,
        id=f"{job_id}_manual_{pd.Timestamp.now().timestamp()}", # 临时任务ID
        misfire_grace_time=3600
    )
    
    return BaseResponse(
        success=True,
        code="JOB_TRIGGERED",
        message=f"已触发任务 '{job_id}'",
        data="triggered"
    )


@router.post(
    "/jobs/{job_id}/stop",
    response_model=BaseResponse[str],
    summary="停止指定定时任务"
)
async def stop_job(job_id: str):
    scheduler = SchedulerService.get_scheduler()
    
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
        msg = f"已停止任务 '{job_id}'"
    else:
        msg = f"任务 '{job_id}' 未运行"
        
    return BaseResponse(
        success=True,
        code="JOB_STOPPED",
        message=msg,
        data="stopped"
    )
