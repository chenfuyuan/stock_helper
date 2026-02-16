"""DailySyncService 测试。

测试日线数据同步服务的增量同步和历史同步功能。
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from src.modules.data_engineering.application.services.daily_sync_service import (
    DailySyncService,
)
from src.modules.data_engineering.domain.model.sync_task import SyncTask


# =============================================================================
# 测试类基础功能
# =============================================================================

def test_daily_sync_service_service_name():
    """测试服务名称返回正确。"""
    
    service = DailySyncService()
    assert service._get_service_name() == "DailySyncService"


def test_daily_sync_service_inheritance():
    """测试 DailySyncService 正确继承基类。"""
    
    service = DailySyncService()
    
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
    mock_sync_use_case_factory,
):
    """测试指定目标日期的增量同步。"""
    
    service = DailySyncService()
    
    # 模拟同步引擎返回值
    expected_result = {
        "synced_dates": ["20250215"],
        "total_count": 150,
        "message": "同步成功",
    }
    
    mock_engine = mock_sync_use_case_factory.create_sync_engine.return_value.__aenter__.return_value
    mock_engine.run_incremental_daily_sync = AsyncMock(return_value=expected_result)
    
    # 执行测试
    result = await service.run_incremental_sync(target_date="20250215")
    
    # 验证结果
    assert result == expected_result
    
    # 验证调用参数
    mock_engine.run_incremental_daily_sync.assert_called_once_with(target_date="20250215")


@pytest.mark.asyncio
async def test_run_incremental_sync_without_target_date(
    mock_async_session_local,
    mock_execution_tracker,
    mock_sync_use_case_factory,
):
    """测试使用默认日期的增量同步。"""
    
    service = DailySyncService()
    
    # 模拟同步引擎返回值
    expected_result = {
        "synced_dates": ["20250216"],
        "total_count": 120,
        "message": "同步成功",
    }
    
    mock_engine = mock_sync_use_case_factory.create_sync_engine.return_value.__aenter__.return_value
    mock_engine.run_incremental_daily_sync = AsyncMock(return_value=expected_result)
    
    # 模拟当前日期
    with patch('src.modules.data_engineering.application.services.daily_sync_service.datetime') as mock_datetime_class:
        mock_now = MagicMock()
        mock_now.strftime.return_value = "20250216"
        mock_datetime_class.now.return_value = mock_now
        
        # 执行测试
        result = await service.run_incremental_sync()
        
        # 验证结果
        assert result == expected_result
        
        # 验证调用参数使用了默认日期
        mock_engine.run_incremental_daily_sync.assert_called_once_with(target_date="20250216")


@pytest.mark.asyncio
async def test_run_incremental_sync_exception_handling(
    mock_async_session_local,
    mock_execution_tracker,
    mock_sync_use_case_factory,
):
    """测试增量同步异常处理。"""
    
    service = DailySyncService()
    
    # 模拟同步引擎抛出异常
    mock_engine = mock_sync_use_case_factory.create_sync_engine.return_value.__aenter__.return_value
    mock_engine.run_incremental_daily_sync = AsyncMock(side_effect=ConnectionError("网络连接失败"))
    
    # 验证异常被正确传播
    with pytest.raises(ConnectionError, match="网络连接失败"):
        await service.run_incremental_sync(target_date="20250215")
    
    # 验证调用
    mock_engine.run_incremental_daily_sync.assert_called_once_with(target_date="20250215")


@pytest.mark.asyncio
async def test_run_incremental_sync_tracking_integration(
    mock_async_session_local,
    mock_execution_tracker,
    mock_sync_use_case_factory,
):
    """测试增量同步与追踪系统的集成。"""
    
    service = DailySyncService()
    
    # 模拟同步引擎返回值
    expected_result = {"synced_dates": ["20250215"], "total_count": 100}
    
    mock_engine = mock_sync_use_case_factory.create_sync_engine.return_value.__aenter__.return_value
    mock_engine.run_incremental_daily_sync = AsyncMock(return_value=expected_result)
    
    # 执行测试
    result = await service.run_incremental_sync(target_date="20250215")
    
    # 验证结果
    assert result == expected_result
    
    # 验证 ExecutionTracker 被正确调用
    mock_execution_tracker.assert_called_once()
    call_kwargs = mock_execution_tracker.call_args[1]
    assert call_kwargs['job_id'] == "sync_daily_by_date"


# =============================================================================
# run_history_sync 方法测试
# =============================================================================

@pytest.mark.asyncio
async def test_run_history_sync_success(
    mock_async_session_local,
    mock_execution_tracker,
    mock_sync_use_case_factory,
):
    """测试历史同步成功场景。"""
    
    service = DailySyncService()
    
    # 模拟同步引擎返回值
    expected_task = create_mock_sync_task(
        task_id="history-task-123",
        status="running",
        total_processed=5000,
    )
    
    mock_engine = mock_sync_use_case_factory.create_sync_engine.return_value.__aenter__.return_value
    mock_engine.run_history_sync = AsyncMock(return_value=expected_task)
    
    # 执行测试
    result = await service.run_history_sync()
    
    # 验证结果
    assert result == expected_task
    
    # 验证调用参数
    mock_engine.run_history_sync.assert_called_once()
    call_args = mock_engine.run_history_sync.call_args[1]
    
    # 验证配置参数
    assert call_args['job_type'].value == "DAILY_HISTORY"
    assert 'config' in call_args
    assert 'batch_size' in call_args['config']


@pytest.mark.asyncio
async def test_run_history_sync_config_parameters(
    mock_async_session_local,
    mock_execution_tracker,
    mock_sync_use_case_factory,
):
    """测试历史同步配置参数传递。"""
    
    service = DailySyncService()
    
    # 模拟同步引擎返回值
    expected_task = create_mock_sync_task()
    
    mock_engine = mock_sync_use_case_factory.create_sync_engine.return_value.__aenter__.return_value
    mock_engine.run_history_sync = AsyncMock(return_value=expected_task)
    
    # 执行测试
    result = await service.run_history_sync()
    
    # 验证结果
    assert result == expected_task
    
    # 验证配置参数
    call_args = mock_engine.run_history_sync.call_args[1]
    config = call_args['config']
    
    # 验证批次大小配置
    assert 'batch_size' in config
    # 注意：这里我们验证配置存在，具体值由 de_config 决定


@pytest.mark.asyncio
async def test_run_history_sync_exception_handling(
    mock_async_session_local,
    mock_execution_tracker,
    mock_sync_use_case_factory,
):
    """测试历史同步异常处理。"""
    
    service = DailySyncService()
    
    # 模拟同步引擎抛出异常
    mock_engine = mock_sync_use_case_factory.create_sync_engine.return_value.__aenter__.return_value
    mock_engine.run_history_sync = AsyncMock(side_effect=ValueError("无效的配置参数"))
    
    # 验证异常被正确传播
    with pytest.raises(ValueError, match="无效的配置参数"):
        await service.run_history_sync()
    
    # 验证调用
    mock_engine.run_history_sync.assert_called_once()


@pytest.mark.asyncio
async def test_run_history_sync_tracking_integration(
    mock_async_session_local,
    mock_execution_tracker,
    mock_sync_use_case_factory,
):
    """测试历史同步与追踪系统的集成。"""
    
    service = DailySyncService()
    
    # 模拟同步引擎返回值
    expected_task = create_mock_sync_task()
    
    mock_engine = mock_sync_use_case_factory.create_sync_engine.return_value.__aenter__.return_value
    mock_engine.run_history_sync = AsyncMock(return_value=expected_task)
    
    # 执行测试
    result = await service.run_history_sync()
    
    # 验证结果
    assert result == expected_task
    
    # 验证 ExecutionTracker 被正确调用
    mock_execution_tracker.assert_called_once()
    call_kwargs = mock_execution_tracker.call_args[1]
    assert call_kwargs['job_id'] == "sync_daily_history"


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
    from unittest.mock import MagicMock
    
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
async def test_daily_sync_service_integration(
    mock_async_session_local,
    mock_execution_tracker,
    mock_sync_use_case_factory,
):
    """测试 DailySyncService 的集成功能。"""
    
    service = DailySyncService()
    
    # 测试两个方法都能正常工作
    # 1. 增量同步
    incremental_result = {"synced_dates": ["20250215"], "total_count": 100}
    mock_engine = mock_sync_use_case_factory.create_sync_engine.return_value.__aenter__.return_value
    mock_engine.run_incremental_daily_sync = AsyncMock(return_value=incremental_result)
    
    result1 = await service.run_incremental_sync(target_date="20250215")
    assert result1 == incremental_result
    
    # 2. 历史同步
    history_task = create_mock_sync_task()
    mock_engine.run_history_sync = AsyncMock(return_value=history_task)
    
    result2 = await service.run_history_sync()
    assert result2 == history_task
    
    # 验证两个方法都使用了追踪系统
    assert mock_execution_tracker.call_count == 2
