"""MarketDataSyncService 测试。

测试 AkShare 市场数据同步服务的功能。
"""

from datetime import datetime, date
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from src.modules.data_engineering.application.dtos.sync_result_dtos import (
    AkShareSyncResult,
)
from src.modules.data_engineering.application.services.market_data_sync_service import (
    MarketDataSyncService,
)


# =============================================================================
# 测试类基础功能
# =============================================================================

def test_market_data_sync_service_service_name():
    """测试服务名称返回正确。"""
    
    service = MarketDataSyncService()
    assert service._get_service_name() == "MarketDataSyncService"


def test_market_data_sync_service_inheritance():
    """测试 MarketDataSyncService 正确继承基类。"""
    
    service = MarketDataSyncService()
    
    # 验证继承关系
    from src.modules.data_engineering.application.services.base.sync_service_base import (
        SyncServiceBase,
    )
    assert isinstance(service, SyncServiceBase)
    
    # 验证基类方法可用
    assert hasattr(service, '_execute_with_tracking')
    assert hasattr(service, '_logger')


# =============================================================================
# run_sync 方法测试
# =============================================================================

@pytest.mark.asyncio
async def test_run_sync_with_target_date(
    mock_async_session_local,
    mock_execution_tracker,
):
    """测试指定目标日期的市场数据同步。"""
    
    service = MarketDataSyncService()
    
    # 模拟 AkShare 同步结果
    expected_result = MagicMock(spec=AkShareSyncResult)
    expected_result.trade_date = date(2025, 2, 15)
    expected_result.limit_up_pool_count = 50
    expected_result.broken_board_count = 20
    expected_result.previous_limit_up_count = 45
    expected_result.dragon_tiger_count = 30
    expected_result.sector_capital_flow_count = 25
    expected_result.errors = []
    
    with patch('src.modules.data_engineering.application.services.market_data_sync_service.DataEngineeringContainer') as mock_container_class:
        # 模拟容器和命令
        mock_container = MagicMock()
        mock_sync_cmd = MagicMock()
        mock_sync_cmd.execute = AsyncMock(return_value=expected_result)
        
        mock_container.get_sync_akshare_market_data_cmd.return_value = mock_sync_cmd
        mock_container_class.return_value = mock_container
        
        # 执行测试
        result = await service.run_sync(target_date="20250215")
        
        # 验证结果
        assert result == expected_result
        
        # 验证调用参数
        mock_sync_cmd.execute.assert_called_once_with(trade_date=date(2025, 2, 15))


@pytest.mark.asyncio
async def test_run_sync_without_target_date(
    mock_async_session_local,
    mock_execution_tracker,
):
    """测试使用默认日期的市场数据同步。"""
    
    service = MarketDataSyncService()
    
    # 模拟 AkShare 同步结果
    expected_result = MagicMock(spec=AkShareSyncResult)
    expected_result.trade_date = date(2025, 2, 16)
    expected_result.limit_up_pool_count = 55
    expected_result.broken_board_count = 18
    expected_result.previous_limit_up_count = 48
    expected_result.dragon_tiger_count = 32
    expected_result.sector_capital_flow_count = 28
    expected_result.errors = []
    
    with patch('src.modules.data_engineering.application.services.market_data_sync_service.DataEngineeringContainer') as mock_container_class:
        mock_container = MagicMock()
        mock_sync_cmd = MagicMock()
        mock_sync_cmd.execute = AsyncMock(return_value=expected_result)
        
        mock_container.get_sync_akshare_market_data_cmd.return_value = mock_sync_cmd
        mock_container_class.return_value = mock_container
        
        # 模拟当前日期
        with patch('src.modules.data_engineering.application.services.market_data_sync_service.datetime') as mock_datetime_class:
            mock_today = date(2025, 2, 16)
            mock_datetime_class.now.return_value = MagicMock()
            mock_datetime_class.now.return_value.date.return_value = mock_today
            
            # 执行测试
            result = await service.run_sync()
            
            # 验证结果
            assert result == expected_result
            
            # 验证调用参数使用了默认日期
            mock_sync_cmd.execute.assert_called_once_with(trade_date=mock_today)


@pytest.mark.asyncio
async def test_run_sync_with_errors(
    mock_async_session_local,
    mock_execution_tracker,
):
    """测试市场数据同步包含错误的情况。"""
    
    service = MarketDataSyncService()
    
    # 模拟包含错误的 AkShare 同步结果
    expected_result = MagicMock(spec=AkShareSyncResult)
    expected_result.trade_date = date(2025, 2, 15)
    expected_result.limit_up_pool_count = 45
    expected_result.broken_board_count = 0  # 炸板池同步失败
    expected_result.previous_limit_up_count = 40
    expected_result.dragon_tiger_count = 25
    expected_result.sector_capital_flow_count = 20
    expected_result.errors = ["炸板池数据同步失败: 网络连接超时", "板块资金流向同步失败: 数据格式错误"]
    
    with patch('src.modules.data_engineering.application.services.market_data_sync_service.DataEngineeringContainer') as mock_container_class:
        mock_container = MagicMock()
        mock_sync_cmd = MagicMock()
        mock_sync_cmd.execute = AsyncMock(return_value=expected_result)
        
        mock_container.get_sync_akshare_market_data_cmd.return_value = mock_sync_cmd
        mock_container_class.return_value = mock_container
        
        # 执行测试
        result = await service.run_sync(target_date="20250215")
        
        # 验证结果包含错误
        assert result == expected_result
        assert len(result.errors) == 2
        assert "炸板池数据同步失败" in result.errors[0]
        assert "板块资金流向同步失败" in result.errors[1]


@pytest.mark.asyncio
async def test_run_sync_exception_handling(
    mock_async_session_local,
    mock_execution_tracker,
):
    """测试市场数据同步异常处理。"""
    
    service = MarketDataSyncService()
    
    with patch('src.modules.data_engineering.application.services.market_data_sync_service.DataEngineeringContainer') as mock_container_class:
        mock_container = MagicMock()
        mock_sync_cmd = MagicMock()
        mock_sync_cmd.execute = AsyncMock(side_effect=ConnectionError("AkShare API 连接失败"))
        
        mock_container.get_sync_akshare_market_data_cmd.return_value = mock_sync_cmd
        mock_container_class.return_value = mock_container
        
        # 验证异常被正确传播
        with pytest.raises(ConnectionError, match="AkShare API 连接失败"):
            await service.run_sync(target_date="20250215")
        
        # 验证调用
        mock_sync_cmd.execute.assert_called_once_with(trade_date=date(2025, 2, 15))


@pytest.mark.asyncio
async def test_run_sync_tracking_integration(
    mock_async_session_local,
    mock_execution_tracker,
):
    """测试市场数据同步与追踪系统的集成。"""
    
    service = MarketDataSyncService()
    
    expected_result = MagicMock(spec=AkShareSyncResult)
    
    with patch('src.modules.data_engineering.application.services.market_data_sync_service.DataEngineeringContainer') as mock_container_class:
        mock_container = MagicMock()
        mock_sync_cmd = MagicMock()
        mock_sync_cmd.execute = AsyncMock(return_value=expected_result)
        
        mock_container.get_sync_akshare_market_data_cmd.return_value = mock_sync_cmd
        mock_container_class.return_value = mock_container
        
        # 执行测试
        result = await service.run_sync(target_date="20250215")
        
        # 验证结果
        assert result == expected_result
        
        # 验证 ExecutionTracker 被正确调用
        mock_execution_tracker.assert_called_once()
        call_kwargs = mock_execution_tracker.call_args[1]
        assert call_kwargs['job_id'] == "sync_akshare_market_data"


@pytest.mark.asyncio
async def test_run_sync_date_format_validation(
    mock_async_session_local,
    mock_execution_tracker,
):
    """测试日期格式验证。"""
    
    service = MarketDataSyncService()
    
    expected_result = MagicMock(spec=AkShareSyncResult)
    
    with patch('src.modules.data_engineering.application.services.market_data_sync_service.DataEngineeringContainer') as mock_container_class:
        mock_container = MagicMock()
        mock_sync_cmd = MagicMock()
        mock_sync_cmd.execute = AsyncMock(return_value=expected_result)
        
        mock_container.get_sync_akshare_market_data_cmd.return_value = mock_sync_cmd
        mock_container_class.return_value = mock_container
        
        # 测试不同的日期格式
        test_dates = ["20250215", "20251231", "20240101"]
        expected_dates = [date(2025, 2, 15), date(2025, 12, 31), date(2024, 1, 1)]
        
        for target_date, expected_trade_date in zip(test_dates, expected_dates):
            result = await service.run_sync(target_date=target_date)
            assert result == expected_result
            mock_sync_cmd.execute.assert_called_with(trade_date=expected_trade_date)


@pytest.mark.asyncio
async def test_run_sync_container_integration(
    mock_async_session_local,
    mock_execution_tracker,
):
    """测试与容器系统的集成。"""
    
    service = MarketDataSyncService()
    
    expected_result = MagicMock(spec=AkShareSyncResult)
    
    with patch('src.modules.data_engineering.application.services.market_data_sync_service.DataEngineeringContainer') as mock_container_class:
        mock_container = MagicMock()
        mock_sync_cmd = MagicMock()
        mock_sync_cmd.execute = AsyncMock(return_value=expected_result)
        
        mock_container.get_sync_akshare_market_data_cmd.return_value = mock_sync_cmd
        mock_container_class.return_value = mock_container
        
        # 执行测试
        result = await service.run_sync(target_date="20250215")
        
        # 验证容器被正确创建
        mock_container_class.assert_called_once()
        
        # 验证命令被正确获取
        mock_container.get_sync_akshare_market_data_cmd.assert_called_once()
        
        # 验证结果
        assert result == expected_result


# =============================================================================
# 边界条件测试
# =============================================================================

@pytest.mark.asyncio
async def test_run_sync_empty_result(
    mock_async_session_local,
    mock_execution_tracker,
):
    """测试空结果的处理。"""
    
    service = MarketDataSyncService()
    
    # 模拟空结果
    expected_result = MagicMock(spec=AkShareSyncResult)
    expected_result.trade_date = date(2025, 2, 15)
    expected_result.limit_up_pool_count = 0
    expected_result.broken_board_count = 0
    expected_result.previous_limit_up_count = 0
    expected_result.dragon_tiger_count = 0
    expected_result.sector_capital_flow_count = 0
    expected_result.errors = []
    
    with patch('src.modules.data_engineering.application.services.market_data_sync_service.DataEngineeringContainer') as mock_container_class:
        mock_container = MagicMock()
        mock_sync_cmd = MagicMock()
        mock_sync_cmd.execute = AsyncMock(return_value=expected_result)
        
        mock_container.get_sync_akshare_market_data_cmd.return_value = mock_sync_cmd
        mock_container_class.return_value = mock_container
        
        # 执行测试
        result = await service.run_sync(target_date="20250215")
        
        # 验证空结果被正确处理
        assert result == expected_result
        assert result.limit_up_pool_count == 0
        assert result.broken_board_count == 0
        assert len(result.errors) == 0


@pytest.mark.asyncio
async def test_run_sync_partial_failure(
    mock_async_session_local,
    mock_execution_tracker,
):
    """测试部分失败的情况（错误隔离）。"""
    
    service = MarketDataSyncService()
    
    # 模拟部分失败的结果
    expected_result = MagicMock(spec=AkShareSyncResult)
    expected_result.trade_date = date(2025, 2, 15)
    expected_result.limit_up_pool_count = 50  # 成功
    expected_result.broken_board_count = 0    # 失败
    expected_result.previous_limit_up_count = 45  # 成功
    expected_result.dragon_tiger_count = 0     # 失败
    expected_result.sector_capital_flow_count = 25  # 成功
    expected_result.errors = [
        "炸板池数据同步失败: 数据源不可用",
        "龙虎榜数据同步失败: API 限流",
    ]
    
    with patch('src.modules.data_engineering.application.services.market_data_sync_service.DataEngineeringContainer') as mock_container_class:
        mock_container = MagicMock()
        mock_sync_cmd = MagicMock()
        mock_sync_cmd.execute = AsyncMock(return_value=expected_result)
        
        mock_container.get_sync_akshare_market_data_cmd.return_value = mock_sync_cmd
        mock_container_class.return_value = mock_container
        
        # 执行测试
        result = await service.run_sync(target_date="20250215")
        
        # 验证部分失败被正确处理
        assert result == expected_result
        assert result.limit_up_pool_count == 50  # 成功的同步
        assert result.broken_board_count == 0    # 失败的同步
        assert len(result.errors) == 2          # 记录了错误
        
        # 验证仍然返回了结果（错误隔离）
        assert result.trade_date == date(2025, 2, 15)
