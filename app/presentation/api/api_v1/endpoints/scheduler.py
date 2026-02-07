from fastapi import APIRouter, status, HTTPException, Body
from app.application.dtos import BaseResponse
from app.core.scheduler import SchedulerService
from app.jobs.sync_job import sync_history_daily_data_job, sync_daily_by_date_job
from pydantic import BaseModel
from typing import Dict, Callable, Any, Optional

router = APIRouter()

# 任务注册表：将任务 ID 映射到具体的任务函数
JOB_REGISTRY: Dict[str, Callable] = {
    "sync_daily_history": sync_history_daily_data_job,  # 历史数据同步（全量/断点续传）
    "sync_daily_by_date": sync_daily_by_date_job,       # 按日期同步（每日增量）
}

class SchedulerStatusResponse(BaseModel):
    is_running: bool
    jobs: list[str]

@router.get(
    "/status",
    response_model=BaseResponse[SchedulerStatusResponse],
    summary="获取调度器状态"
)
async def get_status():
    scheduler = SchedulerService.get_scheduler()
    jobs = [job.id for job in scheduler.get_jobs()]
    
    return BaseResponse(
        success=True,
        code="SCHEDULER_STATUS",
        message="获取状态成功",
        data=SchedulerStatusResponse(
            is_running=scheduler.running,
            jobs=jobs
        )
    )

@router.post(
    "/jobs/{job_id}/start",
    response_model=BaseResponse[str],
    summary="启动指定定时任务"
)
async def start_job(
    job_id: str, 
    interval_minutes: int = Body(..., embed=True, description="执行间隔(分钟)")
):
    """
    启动一个定时任务
    :param job_id: 任务ID (目前支持: sync_daily_history)
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

@router.post(
    "/jobs/{job_id}/trigger",
    response_model=BaseResponse[str],
    summary="立即手动触发一次任务"
)
async def trigger_job_once(
    job_id: str,
    kwargs: Optional[Dict[str, Any]] = Body(None, description="传递给任务的关键字参数，例如: {'trade_date': '20260207'}")
):
    """
    立即在后台运行一次指定任务，不影响定时设置。
    可以传递参数给任务函数。
    """
    if job_id not in JOB_REGISTRY:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found. Available jobs: {list(JOB_REGISTRY.keys())}"
        )
        
    scheduler = SchedulerService.get_scheduler()
    job_func = JOB_REGISTRY[job_id]
    
    # 立即执行不需要 ID，因为它是一次性的
    # 如果有参数，通过 kwargs 传递
    scheduler.add_job(job_func, kwargs=kwargs or {})
    
    return BaseResponse(
        success=True,
        code="JOB_TRIGGERED",
        message=f"已触发任务 '{job_id}' 后台执行一次，参数: {kwargs}",
        data="triggered"
    )

