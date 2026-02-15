"""测试 SchedulerApplicationService 新增方法

对应规格：openspec/changes/refactor-scheduler-to-foundation/specs/foundation-scheduler-service/spec.md

验证目标：
- schedule_and_persist_job(): 调度 + 持久化原子编排
- stop_and_disable_job(): 移除任务 + 更新 DB enabled=False
- trigger_job(): 通过 Port 手动触发任务
- query_execution_logs(): 通过 Repository 查询执行历史
- remove_job() 不再使用 hasattr() hack
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List

import pytest

from src.modules.foundation.application.services.scheduler_application_service import (
    SchedulerApplicationService
)
from src.modules.foundation.domain.ports.scheduler_port import SchedulerPort
from src.modules.foundation.domain.ports.scheduler_job_config_repository_port import (
    SchedulerJobConfigRepositoryPort
)
from src.modules.foundation.domain.dtos.scheduler_dtos import JobConfigDTO
from src.modules.foundation.domain.exceptions import (
    SchedulerJobNotFoundException,
    SchedulerExecutionException,
)


@pytest.fixture
def mock_scheduler_port():
    """Mock SchedulerPort"""
    port = AsyncMock(spec=SchedulerPort)
    return port


@pytest.fixture
def mock_repo_port():
    """Mock SchedulerJobConfigRepositoryPort"""
    repo = AsyncMock(spec=SchedulerJobConfigRepositoryPort)
    return repo


@pytest.fixture
def mock_execution_log_repo():
    """Mock SchedulerExecutionLogRepository (DI注入)"""
    repo = AsyncMock()
    repo.get_by_job_id = AsyncMock(return_value=[])
    repo.get_recent = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def scheduler_service(mock_scheduler_port, mock_repo_port, mock_execution_log_repo):
    """创建 SchedulerApplicationService 实例"""
    # 注意：这里需要修改 SchedulerApplicationService 构造器接受 execution_log_repo
    service = SchedulerApplicationService(
        scheduler_port=mock_scheduler_port,
        scheduler_job_config_repo_port=mock_repo_port,
        scheduler_execution_log_repo_port=mock_execution_log_repo,
    )
    return service


@pytest.fixture
def sample_job_config():
    """示例任务配置"""
    return JobConfigDTO(
        job_id="test_job_123",
        job_name="测试任务",
        cron_expression="0 0 * * *",
        timezone="Asia/Shanghai",
        enabled=True,
        job_kwargs={}
    )


class TestScheduleAndPersistJob:
    """测试 schedule_and_persist_job() 方法 - 调度 + 持久化原子编排"""

    @pytest.mark.asyncio
    async def test_schedule_and_persist_job_success(
        self, scheduler_service, mock_scheduler_port, mock_repo_port, sample_job_config
    ):
        """成功调度并持久化任务"""
        job_registry = {"test_job_123": AsyncMock()}
        
        # Mock repository upsert 操作
        mock_repo_port.upsert = AsyncMock()
        
        await scheduler_service.schedule_and_persist_job(sample_job_config, job_registry)
        
        # 验证调用了 Port 的 schedule_job
        mock_scheduler_port.schedule_job.assert_called_once()
        
        # 验证调用了 Repository 的 upsert
        mock_repo_port.upsert.assert_called_once_with(sample_job_config)

    @pytest.mark.asyncio
    async def test_schedule_and_persist_job_rollback_on_persistence_failure(
        self, scheduler_service, mock_scheduler_port, mock_repo_port, sample_job_config
    ):
        """持久化失败时回滚调度操作"""
        job_registry = {"test_job_123": AsyncMock()}
        
        # Mock repository upsert 失败
        mock_repo_port.upsert = AsyncMock(side_effect=Exception("DB 写入失败"))
        
        with pytest.raises(SchedulerExecutionException) as exc_info:
            await scheduler_service.schedule_and_persist_job(sample_job_config, job_registry)
        
        # 验证异常消息
        assert "持久化失败" in str(exc_info.value.message) or "DB 写入失败" in str(exc_info.value.message)
        
        # 验证调用了 Port 的 remove_job 进行回滚
        mock_scheduler_port.remove_job.assert_called_once_with(sample_job_config.job_id)

    @pytest.mark.asyncio
    async def test_schedule_and_persist_job_not_in_registry(
        self, scheduler_service, sample_job_config
    ):
        """任务不在注册表中，抛出异常"""
        job_registry = {}  # 空注册表
        
        with pytest.raises(SchedulerJobNotFoundException):
            await scheduler_service.schedule_and_persist_job(sample_job_config, job_registry)


class TestStopAndDisableJob:
    """测试 stop_and_disable_job() 方法 - 移除任务 + 更新 DB enabled=False"""

    @pytest.mark.asyncio
    async def test_stop_and_disable_job_success(
        self, scheduler_service, mock_scheduler_port, mock_repo_port
    ):
        """成功停止并禁用任务"""
        job_id = "test_job_456"
        
        # Mock repository update_enabled 操作
        mock_repo_port.update_enabled = AsyncMock()
        
        await scheduler_service.stop_and_disable_job(job_id)
        
        # 验证调用了 Port 的 remove_job
        mock_scheduler_port.remove_job.assert_called_once_with(job_id)
        
        # 验证调用了 Repository 的 update_enabled(job_id, False)
        mock_repo_port.update_enabled.assert_called_once_with(job_id, False)

    @pytest.mark.asyncio
    async def test_stop_and_disable_job_not_found(
        self, scheduler_service, mock_scheduler_port, mock_repo_port
    ):
        """任务不存在，Repository update 应该幂等处理"""
        job_id = "non_existent_job"
        
        # Mock repository update_enabled 返回 False（未更新）
        mock_repo_port.update_enabled = AsyncMock(return_value=False)
        
        # 不应抛出异常，幂等操作
        await scheduler_service.stop_and_disable_job(job_id)
        
        mock_scheduler_port.remove_job.assert_called_once_with(job_id)
        mock_repo_port.update_enabled.assert_called_once()


class TestTriggerJob:
    """测试 trigger_job() 方法 - 通过 Port 手动触发任务"""

    @pytest.mark.asyncio
    async def test_trigger_job_success(self, scheduler_service, mock_scheduler_port):
        """成功触发任务"""
        job_id = "test_job_789"
        kwargs = {"param1": "value1"}
        
        await scheduler_service.trigger_job(job_id, **kwargs)
        
        # 验证调用了 Port 的 trigger_job
        mock_scheduler_port.trigger_job.assert_called_once_with(job_id, **kwargs)

    @pytest.mark.asyncio
    async def test_trigger_job_not_found(self, scheduler_service, mock_scheduler_port):
        """任务不存在时抛出异常"""
        job_id = "non_existent_job"
        
        # Mock Port 抛出 JobNotFoundException
        mock_scheduler_port.trigger_job = AsyncMock(
            side_effect=SchedulerJobNotFoundException(job_id)
        )
        
        with pytest.raises(SchedulerJobNotFoundException):
            await scheduler_service.trigger_job(job_id)


class TestQueryExecutionLogs:
    """测试 query_execution_logs() 方法 - 通过 Repository 查询执行历史"""

    @pytest.mark.asyncio
    async def test_query_execution_logs_by_job_id(
        self, scheduler_service, mock_execution_log_repo
    ):
        """按 job_id 查询执行日志"""
        job_id = "test_job_123"
        mock_logs = [
            {
                "id": 1,
                "job_id": job_id,
                "status": "success",
                "started_at": datetime(2024, 1, 1, 10, 0, 0),
            },
            {
                "id": 2,
                "job_id": job_id,
                "status": "failed",
                "started_at": datetime(2024, 1, 2, 10, 0, 0),
            },
        ]
        mock_execution_log_repo.get_by_job_id = AsyncMock(return_value=mock_logs)
        
        logs = await scheduler_service.query_execution_logs(job_id=job_id)
        
        assert len(logs) == 2
        assert logs[0]["status"] == "success"
        assert logs[1]["status"] == "failed"
        mock_execution_log_repo.get_by_job_id.assert_called_once_with(job_id, limit=100)

    @pytest.mark.asyncio
    async def test_query_execution_logs_recent(
        self, scheduler_service, mock_execution_log_repo
    ):
        """查询最近的执行日志（不指定 job_id）"""
        mock_logs = [
            {"id": 1, "job_id": "job_a", "status": "success"},
            {"id": 2, "job_id": "job_b", "status": "failed"},
        ]
        mock_execution_log_repo.get_recent = AsyncMock(return_value=mock_logs)
        
        logs = await scheduler_service.query_execution_logs(limit=50)
        
        assert len(logs) == 2
        mock_execution_log_repo.get_recent.assert_called_once_with(limit=50)

    @pytest.mark.asyncio
    async def test_query_execution_logs_empty(
        self, scheduler_service, mock_execution_log_repo
    ):
        """查询结果为空"""
        mock_execution_log_repo.get_by_job_id = AsyncMock(return_value=[])
        
        logs = await scheduler_service.query_execution_logs(job_id="non_existent_job")
        
        assert logs == []


class TestRemoveJobNoHasattr:
    """测试 remove_job() 不再使用 hasattr() hack"""

    @pytest.mark.asyncio
    async def test_remove_job_calls_port_directly(
        self, scheduler_service, mock_scheduler_port
    ):
        """验证 remove_job 直接调用 Port 的 remove_job，无 hasattr 检查"""
        job_id = "test_job_999"
        
        await scheduler_service.remove_job(job_id)
        
        # 验证直接调用 Port 的 remove_job（不应有 hasattr 检查）
        mock_scheduler_port.remove_job.assert_called_once_with(job_id)

    @pytest.mark.asyncio
    async def test_remove_job_propagates_exception(
        self, scheduler_service, mock_scheduler_port
    ):
        """验证 remove_job 传播 Port 抛出的异常"""
        job_id = "test_job_error"
        
        mock_scheduler_port.remove_job = AsyncMock(
            side_effect=SchedulerJobNotFoundException(job_id)
        )
        
        with pytest.raises(SchedulerJobNotFoundException):
            await scheduler_service.remove_job(job_id)
