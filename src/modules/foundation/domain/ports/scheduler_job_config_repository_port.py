"""调度器配置仓储端口接口

定义调度器配置持久化操作的抽象契约，建立依赖倒置基础。
所有调度器配置相关的数据操作都通过此接口进行，隐藏具体实现细节。
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from src.modules.foundation.domain.dtos.scheduler_dtos import JobConfigDTO


class SchedulerJobConfigRepositoryPort(ABC):
    """调度器配置仓储端口接口
    
    定义调度器配置的持久化操作能力，包括查询、创建、更新等。
    实现类必须封装具体的数据访问细节（如 SQLAlchemy）。
    """

    @abstractmethod
    async def get_all_enabled(self) -> List[JobConfigDTO]:
        """获取所有启用的调度配置
        
        Returns:
            启用的配置列表，按 job_id 排序
        """
        pass

    @abstractmethod
    async def get_by_job_id(self, job_id: str) -> Optional[JobConfigDTO]:
        """根据 job_id 查询配置
        
        Args:
            job_id: 任务标识
            
        Returns:
            配置记录，不存在时返回 None
        """
        pass

    @abstractmethod
    async def create(self, job_config: JobConfigDTO) -> JobConfigDTO:
        """创建新的调度配置
        
        Args:
            job_config: 要创建的配置
            
        Returns:
            创建后的配置（包含生成的字段）
        """
        pass

    @abstractmethod
    async def update(self, job_config: JobConfigDTO) -> JobConfigDTO:
        """更新调度配置
        
        Args:
            job_config: 要更新的配置
            
        Returns:
            更新后的配置
        """
        pass

    @abstractmethod
    async def upsert(self, job_config: JobConfigDTO) -> JobConfigDTO:
        """创建或更新调度配置（upsert 操作）
        
        Args:
            job_config: 要创建或更新的配置
            
        Returns:
            创建或更新后的配置
        """
        pass

    @abstractmethod
    async def update_enabled(self, job_id: str, enabled: bool) -> bool:
        """更新任务的启用状态
        
        Args:
            job_id: 任务标识
            enabled: 是否启用
            
        Returns:
            是否成功更新
        """
        pass

    @abstractmethod
    async def delete(self, job_id: str) -> bool:
        """删除调度配置
        
        Args:
            job_id: 要删除的任务标识
            
        Returns:
            是否成功删除
        """
        pass
