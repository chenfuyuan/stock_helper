"""调度器配置仓储工厂

创建 Repository 实例时管理会话生命周期。
"""

from sqlalchemy.ext.asyncio import AsyncSession
from src.shared.infrastructure.db.session import AsyncSessionLocal
from src.modules.foundation.infrastructure.persistence.repositories.scheduler_job_config_repo import SchedulerJobConfigRepository


class SchedulerJobConfigRepositoryFactory:
    """调度器配置仓储工厂"""
    
    @staticmethod
    def create() -> SchedulerJobConfigRepository:
        """创建 Repository 实例
        
        Returns:
            配置好的 Repository 实例
        """
        session = AsyncSessionLocal()
        return SchedulerJobConfigRepository(session)
    
    @staticmethod
    async def create_with_session(session: AsyncSession) -> SchedulerJobConfigRepository:
        """使用现有会话创建 Repository 实例
        
        Args:
            session: 现有的数据库会话
            
        Returns:
            配置好的 Repository 实例
        """
        return SchedulerJobConfigRepository(session)
