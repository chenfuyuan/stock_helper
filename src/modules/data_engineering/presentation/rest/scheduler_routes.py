from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

import pandas as pd
from fastapi import APIRouter, Body, Depends, HTTPException, status
from loguru import logger
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

# Updated imports to point to the new location
from src.modules.data_engineering.presentation.jobs.sync_scheduler import (
    sync_daily_data_job,
    sync_finance_history_job,
    sync_history_daily_data_job,
    sync_incremental_finance_job,
    sync_concept_data_job,
    sync_stock_basic_job,
)
from src.modules.data_engineering.presentation.jobs.akshare_market_data_jobs import (
    sync_akshare_market_data_job,
)
from src.shared.dtos import BaseResponse
from src.shared.infrastructure.scheduler.scheduler_service import SchedulerService
from src.shared.infrastructure.scheduler.repositories import (
    SchedulerJobConfigRepository,
    SchedulerExecutionLogRepository,
)
from src.shared.infrastructure.db.session import get_async_session

router = APIRouter()

# 任务注册表：将任务 ID 映射到具体的任务函数
JOB_REGISTRY: Dict[str, Callable] = {
    "sync_daily_history": sync_history_daily_data_job,  # 历史数据同步（全量/断点续传）
    "sync_daily_by_date": sync_daily_data_job,  # 按日期同步（每日增量）- Renamed in new module
    "sync_history_finance": sync_finance_history_job,  # 历史财务数据同步
    "sync_incremental_finance": sync_incremental_finance_job,  # 增量财务数据同步
    "sync_concept_data": sync_concept_data_job,  # 概念数据同步（akshare → PostgreSQL）
    "sync_stock_basic": sync_stock_basic_job,  # 股票基础信息同步（TuShare → PostgreSQL）
    "sync_akshare_market_data": sync_akshare_market_data_job,  # AkShare市场数据同步（涨停池、炸板池等）
}


class JobDetail(BaseModel):
    """
    任务详情 DTO
    """

    id: str = Field(..., description="任务ID")
    name: str = Field(..., description="任务名称")
    next_run_time: Optional[datetime] = Field(None, description="下次运行时间")
    trigger: str = Field(..., description="触发器描述")
    kwargs: Dict[str, Any] = Field(default_factory=dict, description="任务参数")


class SchedulerStatusResponse(BaseModel):
    """
    调度器状态响应 DTO
    """

    is_running: bool = Field(..., description="调度器是否运行中")
    jobs: List[JobDetail] = Field(..., description="当前已调度的任务列表")
    available_jobs: List[str] = Field(..., description="系统支持的可注册任务列表")


@router.get(
    "/status",
    response_model=BaseResponse[SchedulerStatusResponse],
    summary="获取调度器状态",
)
async def get_status():
    """
    获取当前调度器的运行状态以及已注册的任务列表。
    """
    logger.debug("API: get_scheduler_status called")
    scheduler = SchedulerService.get_scheduler()

    current_jobs = []
    for job in scheduler.get_jobs():
        current_jobs.append(
            JobDetail(
                id=job.id,
                name=job.name,
                next_run_time=job.next_run_time,
                trigger=str(job.trigger),
                kwargs=job.kwargs,
            )
        )

    logger.debug(
        f"API: Scheduler status retrieved. Running: {scheduler.running}, "  # noqa: E501
        f"Job Count: {len(current_jobs)}"
    )

    return BaseResponse(
        success=True,
        code="SCHEDULER_STATUS",
        message="获取状态成功",
        data=SchedulerStatusResponse(
            is_running=scheduler.running,
            jobs=current_jobs,
            available_jobs=list(JOB_REGISTRY.keys()),
        ),
    )


@router.post(
    "/jobs/{job_id}/start",
    response_model=BaseResponse[str],
    summary="启动指定定时任务 (Interval 模式)",
)
async def start_job(
    job_id: str,
    interval_minutes: int = Body(..., embed=True, description="执行间隔(分钟)"),
    session: AsyncSession = Depends(get_async_session),
):
    """
    启动一个 Interval 模式的定时任务 (每隔 X 分钟执行一次)
    :param job_id: 任务ID (见 /status 返回的可选列表)
    :param interval_minutes: 间隔分钟数
    """
    logger.info(f"API: start_job called. JobID={job_id}, Interval={interval_minutes}m")

    if job_id not in JOB_REGISTRY:
        logger.warning(f"API: Job not found: {job_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found. Available jobs: {list(JOB_REGISTRY.keys())}",
        )

    scheduler = SchedulerService.get_scheduler()
    job_func = JOB_REGISTRY[job_id]

    # 如果任务已存在，先移除
    if scheduler.get_job(job_id):
        logger.info(f"API: Removing existing job before restart: {job_id}")
        scheduler.remove_job(job_id)

    scheduler.add_job(
        job_func,
        "interval",
        minutes=interval_minutes,
        id=job_id,
        replace_existing=True,
    )
    logger.info(f"API: Job started successfully: {job_id}")

    # 持久化到数据库（interval 模式转换为等效的 cron 表达式）
    repo = SchedulerJobConfigRepository(session)
    cron_expression = f"*/{interval_minutes} * * * *"  # 每 N 分钟执行
    await repo.upsert(
        job_id=job_id,
        job_name=job_id,  # 使用 job_id 作为默认名称
        cron_expression=cron_expression,
        enabled=True,
    )
    logger.info(f"API: Job config persisted to DB: {job_id}")

    return BaseResponse(
        success=True,
        code="JOB_STARTED",
        message=f"已启动任务 '{job_id}'，每 {interval_minutes} 分钟执行一次",
        data="started",
    )


@router.post(
    "/jobs/{job_id}/schedule",
    response_model=BaseResponse[str],
    summary="启动指定定时任务 (Cron 模式)",
)
async def schedule_job(
    job_id: str,
    hour: int = Body(..., embed=True, description="执行小时 (0-23)"),
    minute: int = Body(..., embed=True, description="执行分钟 (0-59)"),
    session: AsyncSession = Depends(get_async_session),
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
            detail=f"Job '{job_id}' not found. Available jobs: {list(JOB_REGISTRY.keys())}",
        )

    scheduler = SchedulerService.get_scheduler()
    job_func = JOB_REGISTRY[job_id]

    # 如果任务已存在，先移除
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)

    scheduler.add_job(
        job_func,
        "cron",
        hour=hour,
        minute=minute,
        id=job_id,
        replace_existing=True,
    )

    # 持久化到数据库
    repo = SchedulerJobConfigRepository(session)
    cron_expression = f"{minute} {hour} * * *"  # 每天 HH:MM 执行
    await repo.upsert(
        job_id=job_id,
        job_name=job_id,  # 使用 job_id 作为默认名称
        cron_expression=cron_expression,
        enabled=True,
    )
    logger.info(f"API: Job config persisted to DB: {job_id}")

    return BaseResponse(
        success=True,
        code="JOB_SCHEDULED",
        message=f"已调度任务 '{job_id}'，每天 {hour:02d}:{minute:02d} 执行",
        data="scheduled",
    )


@router.post(
    "/jobs/{job_id}/trigger",
    response_model=BaseResponse[str],
    summary="立即触发一次任务",
)
async def trigger_job(
    job_id: str,
    params: Optional[Dict[str, Any]] = Body(None, description="任务参数"),
):
    """
    立即异步执行一次任务
    """
    if job_id not in JOB_REGISTRY:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found. Available jobs: {list(JOB_REGISTRY.keys())}",
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
        id=f"{job_id}_manual_{pd.Timestamp.now().timestamp()}",  # 临时任务ID
        misfire_grace_time=3600,
    )

    return BaseResponse(
        success=True,
        code="JOB_TRIGGERED",
        message=f"已触发任务 '{job_id}'",
        data="triggered",
    )


@router.post(
    "/jobs/{job_id}/stop",
    response_model=BaseResponse[str],
    summary="停止指定定时任务",
)
async def stop_job(
    job_id: str,
    session: AsyncSession = Depends(get_async_session),
):
    scheduler = SchedulerService.get_scheduler()

    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
        msg = f"已停止任务 '{job_id}'"
    else:
        msg = f"任务 '{job_id}' 未运行"

    # 更新数据库中的 enabled 状态为 False
    repo = SchedulerJobConfigRepository(session)
    try:
        await repo.update_enabled(job_id=job_id, enabled=False)
        logger.info(f"API: Job config disabled in DB: {job_id}")
    except Exception as e:
        # 如果 DB 中不存在该配置，仅记录警告
        logger.warning(f"API: Failed to disable job config in DB: {job_id}, error: {e}")

    return BaseResponse(success=True, code="JOB_STOPPED", message=msg, data="stopped")


class ExecutionLogDetail(BaseModel):
    """执行日志详情 DTO"""

    job_id: str = Field(..., description="任务标识")
    started_at: datetime = Field(..., description="开始时间")
    finished_at: Optional[datetime] = Field(None, description="结束时间")
    status: str = Field(..., description="执行状态")
    error_message: Optional[str] = Field(None, description="错误信息")
    duration_ms: Optional[int] = Field(None, description="执行耗时（毫秒）")


@router.get(
    "/executions",
    response_model=BaseResponse[List[ExecutionLogDetail]],
    summary="查询调度执行历史",
)
async def get_executions(
    job_id: Optional[str] = None,
    limit: int = 20,
    session: AsyncSession = Depends(get_async_session),
):
    """
    查询调度执行历史记录
    :param job_id: 可选，按任务 ID 筛选
    :param limit: 返回记录数量上限，默认 20，最大 100
    """
    if limit > 100:
        limit = 100

    repo = SchedulerExecutionLogRepository(session)

    if job_id:
        logs = await repo.get_recent_by_job_id(job_id=job_id, limit=limit)
    else:
        logs = await repo.get_recent_all(limit=limit)

    execution_details = [
        ExecutionLogDetail(
            job_id=log.job_id,
            started_at=log.started_at,
            finished_at=log.finished_at,
            status=log.status,
            error_message=log.error_message,
            duration_ms=log.duration_ms,
        )
        for log in logs
    ]

    return BaseResponse(
        success=True,
        code="EXECUTIONS_RETRIEVED",
        message=f"查询到 {len(execution_details)} 条执行记录",
        data=execution_details,
    )
