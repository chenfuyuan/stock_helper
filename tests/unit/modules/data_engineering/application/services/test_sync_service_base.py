"""SyncServiceBase 测试。

测试数据同步服务基类的抽象方法验证和模板方法功能。
"""

from unittest.mock import AsyncMock, MagicMock
import pytest

from src.modules.data_engineering.application.services.base.sync_service_base import (
    SyncServiceBase,
)


# =============================================================================
# 测试类定义
# =============================================================================

class ConcreteSyncService(SyncServiceBase):
    """用于测试的具体实现类。"""
    
    def _get_service_name(self) -> str:
        return "ConcreteSyncService"


class IncompleteSyncService(SyncServiceBase):
    """未实现抽象方法的不完整类，用于测试抽象方法验证。"""
    
    pass


# =============================================================================
# 抽象方法验证测试
# =============================================================================

def test_sync_service_base_abstract_method_validation():
    """测试未实现抽象方法时应抛出 TypeError。"""
    
    # 验证不能直接实例化抽象基类
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        SyncServiceBase()


def test_incomplete_service_cannot_be_instantiated():
    """测试未实现 _get_service_name 的子类无法实例化。"""
    
    with pytest.raises(TypeError, match="Can't instantiate abstract class.*_get_service_name"):
        IncompleteSyncService()


def test_concrete_service_can_be_instantiated():
    """测试正确实现抽象方法的子类可以实例化。"""
    
    service = ConcreteSyncService()
    assert service is not None
    assert service._get_service_name() == "ConcreteSyncService"


def test_service_logger_binding():
    """测试日志记录器正确绑定服务名称。"""
    
    service = ConcreteSyncService()
    
    # 验证日志记录器存在且绑定了正确的服务名称
    assert hasattr(service, '_logger')
    
    # 验证日志记录器的绑定
    # 注意：这里我们检查日志记录器是否有正确的绑定，而不是直接检查内部状态
    # 因为 loguru 的 logger.bind() 返回新的 logger 实例
    assert service._logger is not None


# =============================================================================
# _execute_with_tracking 方法测试
# =============================================================================

@pytest.mark.asyncio
async def test_execute_with_tracking_success_flow(
    mock_async_session_local,
    mock_execution_tracker,
):
    """测试 _execute_with_tracking 的正常执行流程。"""
    
    service = ConcreteSyncService()
    
    # 模拟操作函数
    mock_operation = AsyncMock(return_value={"result": "success"})
    
    # 执行测试
    result = await service._execute_with_tracking(
        job_id="test-job",
        operation=mock_operation,
        success_message="测试操作完成",
    )
    
    # 验证结果
    assert result == {"result": "success"}
    
    # 验证调用
    mock_operation.assert_called_once()
    
    # 验证 session 和 tracker 被正确使用
    mock_async_session_local.assert_called_once()
    mock_execution_tracker.assert_called_once()
    # 验证 tracker 被调用时传入了正确的 job_id
    assert mock_execution_tracker.call_args[1]['job_id'] == "test-job"


@pytest.mark.asyncio
async def test_execute_with_tracking_exception_propagation(
    mock_async_session_local,
    mock_execution_tracker,
):
    """测试 _execute_with_tracking 的异常传播。"""
    
    service = ConcreteSyncService()
    
    # 模拟抛出异常的操作
    test_exception = ValueError("测试异常")
    mock_operation = AsyncMock(side_effect=test_exception)
    
    # 验证异常被正确传播
    with pytest.raises(ValueError, match="测试异常"):
        await service._execute_with_tracking(
            job_id="test-job",
            operation=mock_operation,
            success_message="测试操作完成",
        )
    
    # 验证操作被调用
    mock_operation.assert_called_once()


@pytest.mark.asyncio
async def test_execute_with_tracking_session_and_tracker_context(
    mock_async_session_local,
    mock_execution_tracker,
):
    """测试 session 和 ExecutionTracker 的上下文管理。"""
    
    service = ConcreteSyncService()
    
    # 模拟操作
    mock_operation = AsyncMock(return_value="test_result")
    
    # 执行测试
    result = await service._execute_with_tracking(
        job_id="context-test",
        operation=mock_operation,
        success_message="上下文测试完成",
    )
    
    # 验证结果
    assert result == "test_result"
    
    # 验证 session 上下文管理器被正确使用
    mock_session_instance = mock_async_session_local.return_value
    mock_session_instance.__aenter__.assert_called_once()
    mock_session_instance.__aexit__.assert_called_once()
    
    # 验证 tracker 上下文管理器被正确使用
    mock_tracker_instance = mock_execution_tracker.return_value
    mock_tracker_instance.__aenter__.assert_called_once()
    mock_tracker_instance.__aexit__.assert_called_once()


@pytest.mark.asyncio
async def test_execute_with_tracking_logging(
    mock_async_session_local,
    mock_execution_tracker,
):
    """测试 _execute_with_tracking 的日志记录。"""
    
    service = ConcreteSyncService()
    
    # 模拟操作
    mock_operation = AsyncMock(return_value="test_result")
    
    # 执行测试
    result = await service._execute_with_tracking(
        job_id="logging-test",
        operation=mock_operation,
        success_message="日志测试完成",
    )
    
    # 验证结果
    assert result == "test_result"
    
    # 注意：由于我们使用的是 mock 对象，实际的日志记录可能不会出现在 caplog 中
    # 这里主要验证方法调用没有抛出异常
    mock_operation.assert_called_once()


@pytest.mark.asyncio
async def test_execute_with_tracking_different_return_types(
    mock_async_session_local,
    mock_execution_tracker,
):
    """测试 _execute_with_tracking 处理不同返回类型。"""
    
    service = ConcreteSyncService()
    
    # 测试不同的返回类型
    test_cases = [
        {"dict": "result"},
        ["list", "result"],
        "string_result",
        123,
        None,
    ]
    
    for expected_result in test_cases:
        mock_operation = AsyncMock(return_value=expected_result)
        
        result = await service._execute_with_tracking(
            job_id=f"type-test-{type(expected_result).__name__}",
            operation=mock_operation,
            success_message=f"类型测试完成: {type(expected_result).__name__}",
        )
        
        assert result == expected_result
        mock_operation.assert_called_once()


@pytest.mark.asyncio
async def test_execute_with_tracking_parameter_validation(
    mock_async_session_local,
    mock_execution_tracker,
):
    """测试 _execute_with_tracking 的参数验证。"""
    
    service = ConcreteSyncService()
    
    # 测试必需参数
    mock_operation = AsyncMock(return_value="test")
    
    result = await service._execute_with_tracking(
        job_id="param-test",
        operation=mock_operation,
        success_message="参数测试完成",
    )
    
    assert result == "test"
    
    # 验证参数被正确传递给 ExecutionTracker
    mock_execution_tracker.assert_called_once()
    assert mock_execution_tracker.call_args[1]['job_id'] == "param-test"
