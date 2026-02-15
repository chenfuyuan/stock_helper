"""Scheduler REST API Routes

Foundation模块的调度器HTTP API端点。
所有业务逻辑委托给SchedulerApplicationService，Routes层只负责HTTP映射。
"""

from typing import Dict, Callable, Optional, List

from fastapi import APIRouter, HTTPException, status, Depends
from loguru import logger

from src.shared.dtos import BaseResponse
from src.modules.foundation.application.services.scheduler_application_service import (
    SchedulerApplicationService
)
from src.modules.foundation.application.dtos.scheduler_dtos import (
    JobScheduleRequestDTO,
)
from src.modules.foundation.domain.dtos.scheduler_dtos import JobConfigDTO
from src.modules.foundation.domain.exceptions import (
    SchedulerJobNotFoundException,
    SchedulerJobAlreadyExistsException,
)
from src.modules.foundation.infrastructure.di.container import get_scheduler_service
from src.modules.foundation.presentation.rest.scheduler_schemas import (
    JobDetail,
    SchedulerStatusResponse,
    ExecutionLogDetail,
)

router = APIRouter()


def _get_job_registry() -> Dict[str, Callable]:
    """获取任务注册表
    
    从各业务模块收集注册表。由main.py在启动时注入。
    在Routes中作为临时方案，实际注册表应通过DI注入。
    """
    # TODO: 从DI容器或启动配置获取注册表
    return {}


@router.get(
    "/status",
    response_model=BaseResponse[SchedulerStatusResponse],
    summary="获取调度器状态",
)
async def get_status(
    scheduler_service: SchedulerApplicationService = Depends(get_scheduler_service)
):
    """获取当前调度器的运行状态以及已注册的任务列表"""
    logger.debug("API: get_scheduler_status called")
    
    try:
        all_jobs = await scheduler_service.get_all_jobs_status()
        
        job_details = []
        for job in all_jobs:
            job_detail = JobDetail(
                id=job.get("id", ""),
                name=job.get("job_name", ""),
                next_run_time=job.get("next_run_time"),
                trigger=job.get("trigger", ""),
                kwargs=job.get("kwargs", {}),
            )
            job_details.append(job_detail)
        
        # 获取可用任务列表
        job_registry = _get_job_registry()
        available_jobs = list(job_registry.keys())
        
        response_data = SchedulerStatusResponse(
            is_running=True,
            jobs=job_details,
            available_jobs=available_jobs,
        )
        
        return BaseResponse(
            success=True,
            data=response_data,
            message="获取调度器状态成功"
        )
        
    except Exception as e:
        logger.error(f"获取调度器状态失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取调度器状态失败: {str(e)}"
        )


@router.post(
    "/jobs/schedule",
    response_model=BaseResponse[dict],
    summary="调度任务",
)
async def schedule_job(
    request: JobScheduleRequestDTO,
    scheduler_service: SchedulerApplicationService = Depends(get_scheduler_service)
):
    """调度新任务或更新已有任务的调度计划"""
    logger.info(f"API: schedule_job called for {request.job_id}")
    
    try:
        job_registry = _get_job_registry()
        
        if request.job_id not in job_registry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"任务 {request.job_id} 不在注册表中"
            )
        
        job_config = JobConfigDTO(
            job_id=request.job_id,
            job_name=request.job_name or request.job_id,
            cron_expression=request.cron_expression,
            timezone=request.timezone or "Asia/Shanghai",
            enabled=True,
            job_kwargs=request.job_kwargs or {},
        )
        
        # 委托Application Service进行调度+持久化
        await scheduler_service.schedule_and_persist_job(job_config, job_registry)
        
        return BaseResponse(
            success=True,
            data={"job_id": request.job_id},
            message=f"任务 {request.job_id} 调度成功"
        )
        
    except SchedulerJobAlreadyExistsException as e:
        logger.warning(f"任务已存在: {request.job_id}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"调度任务失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"调度任务失败: {str(e)}"
        )


@router.post(
    "/jobs/{job_id}/start",
    response_model=BaseResponse[dict],
    summary="启动任务",
)
async def start_job(
    job_id: str,
    cron_expression: str,
    timezone: str = "Asia/Shanghai",
    scheduler_service: SchedulerApplicationService = Depends(get_scheduler_service)
):
    """启动指定任务（等同于schedule_job）"""
    logger.info(f"API: start_job called for {job_id}")
    
    try:
        job_registry = _get_job_registry()
        
        if job_id not in job_registry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"任务 {job_id} 不在注册表中"
            )
        
        job_config = JobConfigDTO(
            job_id=job_id,
            job_name=job_id,
            cron_expression=cron_expression,
            timezone=timezone,
            enabled=True,
            job_kwargs={},
        )
        
        await scheduler_service.schedule_and_persist_job(job_config, job_registry)
        
        return BaseResponse(
            success=True,
            data={"job_id": job_id},
            message=f"任务 {job_id} 启动成功"
        )
        
    except Exception as e:
        logger.error(f"启动任务失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"启动任务失败: {str(e)}"
        )


@router.post(
    "/jobs/{job_id}/stop",
    response_model=BaseResponse[dict],
    summary="停止任务",
)
async def stop_job(
    job_id: str,
    scheduler_service: SchedulerApplicationService = Depends(get_scheduler_service)
):
    """停止指定任务并标记为禁用"""
    logger.info(f"API: stop_job called for {job_id}")
    
    try:
        # 委托Application Service停止并禁用任务
        await scheduler_service.stop_and_disable_job(job_id)
        
        return BaseResponse(
            success=True,
            data={"job_id": job_id},
            message=f"任务 {job_id} 已停止"
        )
        
    except SchedulerJobNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"停止任务失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"停止任务失败: {str(e)}"
        )


@router.post(
    "/jobs/{job_id}/trigger",
    response_model=BaseResponse[dict],
    summary="手动触发任务",
)
async def trigger_job(
    job_id: str,
    scheduler_service: SchedulerApplicationService = Depends(get_scheduler_service)
):
    """立即触发指定任务执行一次"""
    logger.info(f"API: trigger_job called for {job_id}")
    
    try:
        # 委托Application Service触发任务
        await scheduler_service.trigger_job(job_id)
        
        return BaseResponse(
            success=True,
            data={"job_id": job_id},
            message=f"任务 {job_id} 已触发执行"
        )
        
    except SchedulerJobNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"触发任务失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"触发任务失败: {str(e)}"
        )


@router.get(
    "/executions",
    response_model=BaseResponse[List[ExecutionLogDetail]],
    summary="查询调度执行历史",
)
async def get_executions(
    job_id: Optional[str] = None,
    limit: int = 20,
    scheduler_service: SchedulerApplicationService = Depends(get_scheduler_service),
):
    """查询调度执行历史记录"""
    if limit > 100:
        limit = 100
    
    try:
        # 委托Application Service查询执行日志
        logs = await scheduler_service.query_execution_logs(job_id=job_id, limit=limit)
        
        execution_details = []
        for log in logs:
            detail = ExecutionLogDetail(
                job_id=log.get("job_id", ""),
                started_at=log.get("started_at"),
                finished_at=log.get("finished_at"),
                status=log.get("status", ""),
                error_message=log.get("error_message"),
                duration_ms=log.get("duration_ms"),
            )
            execution_details.append(detail)
        
        return BaseResponse(
            success=True,
            data=execution_details,
            message="查询执行历史成功"
        )
        
    except Exception as e:
        logger.error(f"查询执行历史失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查询执行历史失败: {str(e)}"
        )
