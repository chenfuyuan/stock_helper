"""FinanceSyncService 测试。

测试财务数据同步服务的增量同步和历史同步功能。
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from src.modules.data_engineering.application.dtos.sync_result_dtos import (
    IncrementalFinanceSyncResult,
)
from src.modules.data_engineering.application.services.finance_sync_service import (
    FinanceSyncService,
)
from src.modules.data_engineering.domain.model.sync_task import SyncTask


# =============================================================================
# 测试类基础功能
# =============================================================================

def test_finance_sync_service_service_name():
    """测试服务名称返回正确。"""
    
    service = FinanceSyncService()
    assert service._get_service_name() == "FinanceSyncService"


def test_finance_sync_service_inheritance():
    """测试 FinanceSyncService 正确继承基类。"""
    
    service = FinanceSyncService()
    
    # 验证继承关系
    from src.modules.data_engineering.application.services.base.sync_service_base import (
        SyncServiceBase,
    )
    assert isinstance(service, SyncServiceBase)
    
    # 验证基类方法可用
    assert hasattr(service, '_execute_with_tracking')
    assert hasattr(service, '_logger')


# =============================================================================
# run_incremental_sync 方法测试
# =============================================================================

@pytest.mark.asyncio
async def test_run_incremental_sync_with_target_date(
    mock_async_session_local,
    mock_execution_tracker,
):
    """测试指定目标日期的增量同步。"""
    
    service = FinanceSyncService()
    
    # 模拟增量财务同步结果
    expected_result = MagicMock(spec=IncrementalFinanceSyncResult)
    expected_result.synced_count = 50
    expected_result.failed_count = 2
    expected_result.retry_count = 1
    expected_result.retry_success_count = 1
    expected_result.target_period = "20250215"
    
    with patch('src.modules.data_engineering.application.services.finance_sync_service.SyncUseCaseFactory') as mock_factory:
        mock_use_case = MagicMock()
        mock_use_case.__aenter__ = AsyncMock(return_value=mock_use_case)
        mock_use_case.execute = AsyncMock(return_value=expected_result)
        mock_factory.create_incremental_finance_use_case.return_value = mock_use_case
        
        # 执行测试
        result = await service.run_incremental_sync(target_date="20250215")
        
        # 验证结果
        assert result == expected_result
        
        # 验证调用参数
        mock_use_case.execute.assert_called_once_with(actual_date="20250215")


@pytest.mark.asyncio
async def test_run_incremental_sync_without_target_date(
    mock_async_session_local,
    mock_execution_tracker,
):
    """测试使用默认日期的增量同步。"""
    
    service = FinanceSyncService()
    
    # 模拟增量财务同步结果
    expected_result = MagicMock(spec=IncrementalFinanceSyncResult)
    expected_result.synced_count = 45
    expected_result.failed_count = 0
    expected_result.retry_count = 0
    expected_result.retry_success_count = 0
    expected_result.target_period = "20250216"
    
    with patch('src.modules.data_engineering.application.services.finance_sync_service.SyncUseCaseFactory') as mock_factory:
        mock_use_case = MagicMock()
        mock_use_case.__aenter__ = AsyncMock(return_value=mock_use_case)
        mock_use_case.execute = AsyncMock(return_value=expected_result)
        mock_factory.create_incremental_finance_use_case.return_value = mock_use_case
        
        # 模拟当前日期
        with patch('src.modules.data_engineering.application.services.finance_sync_service.datetime') as mock_datetime_class:
            mock_now = MagicMock()
            mock_now.strftime.return_value = "20250216"
            mock_datetime_class.now.return_value = mock_now
            
            # 执行测试
            result = await service.run_incremental_sync()
            
            # 验证结果
            assert result == expected_result
            
            # 验证调用参数使用了默认日期
            mock_use_case.execute.assert_called_once_with(actual_date="20250216")


@pytest.mark.asyncio
async def test_run_incremental_sync_exception_handling(
    mock_async_session_local,
    mock_execution_tracker,
):
    """测试增量同步异常处理。"""
    
    service = FinanceSyncService()
    
    with patch('src.modules.data_engineering.application.services.finance_sync_service.SyncUseCaseFactory') as mock_factory:
        mock_use_case = MagicMock()
        mock_use_case.__aenter__ = AsyncMock(return_value=mock_use_case)
        mock_use_case.execute = AsyncMock(side_effect=ConnectionError("财务数据源连接失败"))
        mock_factory.create_incremental_finance_use_case.return_value = mock_use_case
        
        # 验证异常被正确传播
        with pytest.raises(ConnectionError, match="财务数据源连接失败"):
            await service.run_incremental_sync(target_date="20250215")
        
        # 验证调用
        mock_use_case.execute.assert_called_once_with(actual_date="20250215")


@pytest.mark.asyncio
async def test_run_incremental_sync_tracking_integration(
    mock_async_session_local,
    mock_execution_tracker,
):
    """测试增量同步与追踪系统的集成。"""
    
    service = FinanceSyncService()
    
    expected_result = MagicMock(spec=IncrementalFinanceSyncResult)
    
    with patch('src.modules.data_engineering.application.services.finance_sync_service.SyncUseCaseFactory') as mock_factory:
        mock_use_case = MagicMock()
        mock_use_case.__aenter__ = AsyncMock(return_value=mock_use_case)
        mock_use_case.execute = AsyncMock(return_value=expected_result)
        mock_factory.create_incremental_finance_use_case.return_value = mock_use_case
        
        # 执行测试
        result = await service.run_incremental_sync(target_date="20250215")
        
        # 验证结果
        assert result == expected_result
        
        # 验证 ExecutionTracker 被正确调用
        mock_execution_tracker.assert_called_once()
        call_kwargs = mock_execution_tracker.call_args[1]
        assert call_kwargs['job_id'] == "sync_incremental_finance"


# =============================================================================
# run_history_sync 方法测试
# =============================================================================

@pytest.mark.asyncio
async def test_run_history_sync_success(
    mock_async_session_local,
    mock_execution_tracker,
):
    """测试历史同步成功场景。"""
    
    service = FinanceSyncService()
    
    # 模拟同步引擎返回值
    expected_task = create_mock_sync_task(
        task_id="finance-history-task-123",
        status="running",
        total_processed=3000,
    )
    
    with patch('src.modules.data_engineering.application.services.finance_sync_service.SyncUseCaseFactory') as mock_factory:
        mock_engine = MagicMock()
        mock_engine.__aenter__ = AsyncMock(return_value=mock_engine)
        mock_engine.run_history_sync = AsyncMock(return_value=expected_task)
        mock_factory.create_sync_engine.return_value = mock_engine
        
        # 模拟当前日期
        with patch('src.modules.data_engineering.application.services.finance_sync_service.datetime') as mock_datetime_class:
            mock_now = MagicMock()
            mock_now.strftime.return_value = "20250216"
            mock_datetime_class.now.return_value = mock_now
            
            # 执行测试
            result = await service.run_history_sync()
            
            # 验证结果
            assert result == expected_task
            
            # 验证调用参数
            mock_engine.run_history_sync.assert_called_once()
            call_args = mock_engine.run_history_sync.call_args[1]
            
            # 验证配置参数
            assert call_args['job_type'].value == "FINANCE_HISTORY"
            assert 'config' in call_args
            config = call_args['config']
            assert 'batch_size' in config
            assert 'start_date' in config
            assert 'end_date' in config
            assert config['end_date'] == "20250216"


@pytest.mark.asyncio
async def test_run_history_sync_config_parameters(
    mock_async_session_local,
    mock_execution_tracker,
):
    """测试历史同步配置参数传递。"""
    
    service = FinanceSyncService()
    
    expected_task = create_mock_sync_task()
    
    with patch('src.modules.data_engineering.application.services.finance_sync_service.SyncUseCaseFactory') as mock_factory:
        mock_engine = MagicMock()
        mock_engine.__aenter__ = AsyncMock(return_value=mock_engine)
        mock_engine.run_history_sync = AsyncMock(return_value=expected_task)
        mock_factory.create_sync_engine.return_value = mock_engine
        
        # 模拟当前日期
        with patch('src.modules.data_engineering.application.services.finance_sync_service.datetime') as mock_datetime_class:
            mock_now = MagicMock()
            mock_now.strftime.return_value = "20250216"
            mock_datetime_class.now.return_value = mock_now
            
            # 执行测试
            result = await service.run_history_sync()
            
            # 验证结果
            assert result == expected_task
            
            # 验证配置参数
            call_args = mock_engine.run_history_sync.call_args[1]
            config = call_args['config']
            
            # 验证必要的配置项存在
            assert 'batch_size' in config
            assert 'start_date' in config
            assert 'end_date' in config
            assert config['end_date'] == "20250216"


@pytest.mark.asyncio
async def test_run_history_sync_exception_handling(
    mock_async_session_local,
    mock_execution_tracker,
):
    """测试历史同步异常处理。"""
    
    service = FinanceSyncService()
    
    with patch('src.modules.data_engineering.application.services.finance_sync_service.SyncUseCaseFactory') as mock_factory:
        mock_engine = MagicMock()
        mock_engine.__aenter__ = AsyncMock(return_value=mock_engine)
        mock_engine.run_history_sync = AsyncMock(side_effect=ValueError("无效的财务数据配置"))
        mock_factory.create_sync_engine.return_value = mock_engine
        
        # 验证异常被正确传播
        with pytest.raises(ValueError, match="无效的财务数据配置"):
            await service.run_history_sync()
        
        # 验证调用
        mock_engine.run_history_sync.assert_called_once()


@pytest.mark.asyncio
async def test_run_history_sync_tracking_integration(
    mock_async_session_local,
    mock_execution_tracker,
):
    """测试历史同步与追踪系统的集成。"""
    
    service = FinanceSyncService()
    
    expected_task = create_mock_sync_task()
    
    with patch('src.modules.data_engineering.application.services.finance_sync_service.SyncUseCaseFactory') as mock_factory:
        mock_engine = MagicMock()
        mock_engine.__aenter__ = AsyncMock(return_value=mock_engine)
        mock_engine.run_history_sync = AsyncMock(return_value=expected_task)
        mock_factory.create_sync_engine.return_value = mock_engine
        
        # 执行测试
        result = await service.run_history_sync()
        
        # 验证结果
        assert result == expected_task
        
        # 验证 ExecutionTracker 被正确调用
        mock_execution_tracker.assert_called_once()
        call_kwargs = mock_execution_tracker.call_args[1]
        assert call_kwargs['job_id'] == "sync_history_finance"


# =============================================================================
# 辅助函数
# =============================================================================

def create_mock_sync_task(
    task_id: str = "test-task-id",
    status: str = "completed",
    total_processed: int = 100,
) -> SyncTask:
    """创建模拟的 SyncTask 对象。
    
    Args:
        task_id: 任务 ID
        status: 任务状态
        total_processed: 处理的总记录数
        
    Returns:
        配置好的 MagicMock 对象，模拟 SyncTask 的行为
    """
    task = MagicMock(spec=SyncTask)
    task.id = task_id
    # 创建 status mock 对象并设置 value 属性
    task.status = MagicMock()
    task.status.value = status
    task.total_processed = total_processed
    return task


# =============================================================================
# 集成测试
# =============================================================================

@pytest.mark.asyncio
async def test_finance_sync_service_integration(
    mock_async_session_local,
    mock_execution_tracker,
):
    """测试 FinanceSyncService 的集成功能。"""
    
    service = FinanceSyncService()
    
    # 测试两个方法都能正常工作
    # 1. 增量同步
    incremental_result = MagicMock(spec=IncrementalFinanceSyncResult)
    
    with patch('src.modules.data_engineering.application.services.finance_sync_service.SyncUseCaseFactory') as mock_factory:
        mock_use_case = MagicMock()
        mock_use_case.__aenter__ = AsyncMock(return_value=mock_use_case)
        mock_use_case.execute = AsyncMock(return_value=incremental_result)
        mock_factory.create_incremental_finance_use_case.return_value = mock_use_case
        
        result1 = await service.run_incremental_sync(target_date="20250215")
        assert result1 == incremental_result
        
        # 2. 历史同步
        history_task = create_mock_sync_task()
        mock_engine = MagicMock()
        mock_engine.__aenter__ = AsyncMock(return_value=mock_engine)
        mock_engine.run_history_sync = AsyncMock(return_value=history_task)
        mock_factory.create_sync_engine.return_value = mock_engine
        
        result2 = await service.run_history_sync()
        assert result2 == history_task
        
        # 验证两个方法都使用了追踪系统
        assert mock_execution_tracker.call_count == 2
