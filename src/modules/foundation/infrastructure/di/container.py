"""Foundation 模块依赖注入容器

提供 Foundation 模块的依赖注入配置，包括 Scheduler 服务的组装。
"""

from typing import Optional

from src.modules.foundation.domain.ports.scheduler_port import SchedulerPort
from src.modules.foundation.domain.ports.scheduler_job_config_repository_port import (
    SchedulerJobConfigRepositoryPort
)
from src.modules.foundation.infrastructure.adapters.apscheduler_adapter import (
    APSchedulerAdapter
)
from src.modules.foundation.infrastructure.persistence.repositories.scheduler_job_config_repo_factory import (
    SchedulerJobConfigRepositoryFactory
)
from src.modules.foundation.infrastructure.persistence.repositories.scheduler_execution_log_repo import (
    SchedulerExecutionLogRepository
)
from src.modules.foundation.application.services.scheduler_application_service import (
    SchedulerApplicationService
)
from src.shared.infrastructure.db.session import AsyncSessionLocal


# Singleton 实例
_scheduler_adapter_instance: Optional[APSchedulerAdapter] = None
_scheduler_service_instance: Optional[SchedulerApplicationService] = None


def get_scheduler_port() -> SchedulerPort:
    """获取 Scheduler Port 实例（Singleton）
    
    Returns:
        APSchedulerAdapter 实例
    """
    global _scheduler_adapter_instance
    
    if _scheduler_adapter_instance is None:
        _scheduler_adapter_instance = APSchedulerAdapter()
    
    return _scheduler_adapter_instance


def get_scheduler_job_config_repository() -> SchedulerJobConfigRepositoryPort:
    """获取 Job Config Repository 实例
    
    使用 Factory 创建，每次调用返回新实例。
    
    Returns:
        SchedulerJobConfigRepository 实例
    """
    return SchedulerJobConfigRepositoryFactory.create()


def get_scheduler_execution_log_repository() -> SchedulerExecutionLogRepository:
    """获取 Execution Log Repository 实例
    
    使用共享的 AsyncSessionLocal 创建会话。
    
    Returns:
        SchedulerExecutionLogRepository 实例
    """
    session = AsyncSessionLocal()
    return SchedulerExecutionLogRepository(session)


def get_scheduler_service() -> SchedulerApplicationService:
    """获取 Scheduler Application Service 实例（Singleton）
    
    组装所有依赖并返回服务实例。
    
    Returns:
        SchedulerApplicationService 实例
    """
    global _scheduler_service_instance
    
    if _scheduler_service_instance is None:
        scheduler_port = get_scheduler_port()
        job_config_repo = get_scheduler_job_config_repository()
        execution_log_repo = get_scheduler_execution_log_repository()
        
        _scheduler_service_instance = SchedulerApplicationService(
            scheduler_port=scheduler_port,
            scheduler_job_config_repo_port=job_config_repo,
            scheduler_execution_log_repo_port=execution_log_repo,
        )
    
    return _scheduler_service_instance


def reset_container() -> None:
    """重置容器中的所有 Singleton 实例
    
    主要用于测试场景，清理状态以避免测试间的相互影响。
    """
    global _scheduler_adapter_instance, _scheduler_service_instance
    
    _scheduler_adapter_instance = None
    _scheduler_service_instance = None
