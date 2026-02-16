"""BasicDataSyncService 测试。

测试基础数据同步服务的概念同步和股票基础信息同步功能。
"""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from src.modules.data_engineering.application.dtos.sync_result_dtos import (
    ConceptSyncResult,
)
from src.modules.data_engineering.application.services.basic_data_sync_service import (
    BasicDataSyncService,
)


# =============================================================================
# 测试类基础功能
# =============================================================================

def test_basic_data_sync_service_service_name():
    """测试服务名称返回正确。"""
    
    service = BasicDataSyncService()
    assert service._get_service_name() == "BasicDataSyncService"


def test_basic_data_sync_service_inheritance():
    """测试 BasicDataSyncService 正确继承基类。"""
    
    service = BasicDataSyncService()
    
    # 验证继承关系
    from src.modules.data_engineering.application.services.base.sync_service_base import (
        SyncServiceBase,
    )
    assert isinstance(service, SyncServiceBase)
    
    # 验证基类方法可用
    assert hasattr(service, '_execute_with_tracking')
    assert hasattr(service, '_logger')


# =============================================================================
# run_concept_sync 方法测试
# =============================================================================

@pytest.mark.asyncio
async def test_run_concept_sync_success(
    mock_async_session_local,
    mock_execution_tracker,
):
    """测试概念数据同步成功场景。"""
    
    service = BasicDataSyncService()
    
    # 模拟概念同步结果
    expected_result = MagicMock(spec=ConceptSyncResult)
    expected_result.total_concepts = 150
    expected_result.success_concepts = 145
    expected_result.failed_concepts = 5
    expected_result.total_stocks = 3500
    expected_result.elapsed_time = 120.5
    
    with patch('src.modules.data_engineering.application.services.basic_data_sync_service.DataEngineeringContainer') as mock_container_class:
        with patch('src.modules.data_engineering.application.services.basic_data_sync_service.SyncConceptDataCmd') as mock_cmd_class:
            # 模拟容器
            mock_container = MagicMock()
            mock_concept_provider = MagicMock()
            mock_concept_repo = MagicMock()
            
            mock_container.concept_provider.return_value = mock_concept_provider
            mock_container.concept_repository.return_value = mock_concept_repo
            mock_container_class.return_value = mock_container
            
            # 模拟命令
            mock_sync_cmd = MagicMock()
            mock_sync_cmd.execute = AsyncMock(return_value=expected_result)
            mock_cmd_class.return_value = mock_sync_cmd
            
            # 执行测试
            result = await service.run_concept_sync()
            
            # 验证结果
            assert result == expected_result
            
            # 验证命令被正确创建
            mock_cmd_class.assert_called_once_with(
                concept_provider=mock_concept_provider,
                concept_repo=mock_concept_repo,
            )
            
            # 验证命令被执行
            mock_sync_cmd.execute.assert_called_once()


@pytest.mark.asyncio
async def test_run_concept_sync_partial_failure(
    mock_async_session_local,
    mock_execution_tracker,
):
    """测试概念数据同步部分失败场景。"""
    
    service = BasicDataSyncService()
    
    # 模拟部分失败的概念同步结果
    expected_result = MagicMock(spec=ConceptSyncResult)
    expected_result.total_concepts = 150
    expected_result.success_concepts = 120  # 部分成功
    expected_result.failed_concepts = 30    # 部分失败
    expected_result.total_stocks = 2800
    expected_result.elapsed_time = 150.2
    
    with patch('src.modules.data_engineering.application.services.basic_data_sync_service.DataEngineeringContainer') as mock_container_class:
        with patch('src.modules.data_engineering.application.services.basic_data_sync_service.SyncConceptDataCmd') as mock_cmd_class:
            mock_container = MagicMock()
            mock_container.concept_provider.return_value = MagicMock()
            mock_container.concept_repository.return_value = MagicMock()
            mock_container_class.return_value = mock_container
            
            mock_sync_cmd = MagicMock()
            mock_sync_cmd.execute = AsyncMock(return_value=expected_result)
            mock_cmd_class.return_value = mock_sync_cmd
            
            # 执行测试
            result = await service.run_concept_sync()
            
            # 验证部分失败的结果
            assert result == expected_result
            assert result.success_concepts == 120
            assert result.failed_concepts == 30
            assert result.total_concepts == 150


@pytest.mark.asyncio
async def test_run_concept_sync_exception_handling(
    mock_async_session_local,
    mock_execution_tracker,
):
    """测试概念数据同步异常处理。"""
    
    service = BasicDataSyncService()
    
    with patch('src.modules.data_engineering.application.services.basic_data_sync_service.DataEngineeringContainer') as mock_container_class:
        with patch('src.modules.data_engineering.application.services.basic_data_sync_service.SyncConceptDataCmd') as mock_cmd_class:
            mock_container = MagicMock()
            mock_container.concept_provider.return_value = MagicMock()
            mock_container.concept_repository.return_value = MagicMock()
            mock_container_class.return_value = mock_container
            
            mock_sync_cmd = MagicMock()
            mock_sync_cmd.execute = AsyncMock(side_effect=ConnectionError("概念数据源连接失败"))
            mock_cmd_class.return_value = mock_sync_cmd
            
            # 验证异常被正确传播
            with pytest.raises(ConnectionError, match="概念数据源连接失败"):
                await service.run_concept_sync()
            
            # 验证命令被执行
            mock_sync_cmd.execute.assert_called_once()


@pytest.mark.asyncio
async def test_run_concept_sync_tracking_integration(
    mock_async_session_local,
    mock_execution_tracker,
):
    """测试概念数据同步与追踪系统的集成。"""
    
    service = BasicDataSyncService()
    
    expected_result = MagicMock(spec=ConceptSyncResult)
    
    with patch('src.modules.data_engineering.application.services.basic_data_sync_service.DataEngineeringContainer') as mock_container_class:
        with patch('src.modules.data_engineering.application.services.basic_data_sync_service.SyncConceptDataCmd') as mock_cmd_class:
            mock_container = MagicMock()
            mock_container.concept_provider.return_value = MagicMock()
            mock_container.concept_repository.return_value = MagicMock()
            mock_container_class.return_value = mock_container
            
            mock_sync_cmd = MagicMock()
            mock_sync_cmd.execute = AsyncMock(return_value=expected_result)
            mock_cmd_class.return_value = mock_sync_cmd
            
            # 执行测试
            result = await service.run_concept_sync()
            
            # 验证结果
            assert result == expected_result
            
            # 验证 ExecutionTracker 被正确调用
            mock_execution_tracker.assert_called_once()
            call_kwargs = mock_execution_tracker.call_args[1]
            assert call_kwargs['job_id'] == "sync_concept_data"


# =============================================================================
# run_stock_basic_sync 方法测试
# =============================================================================

@pytest.mark.asyncio
async def test_run_stock_basic_sync_success(
    mock_async_session_local,
    mock_execution_tracker,
):
    """测试股票基础信息同步成功场景。"""
    
    service = BasicDataSyncService()
    
    # 模拟用例执行结果
    mock_use_case_result = MagicMock()
    mock_use_case_result.synced_count = 5000
    mock_use_case_result.message = "股票基础信息同步成功"
    mock_use_case_result.status = "success"
    
    # 预期的返回结果
    expected_result = {
        "synced_count": 5000,
        "message": "股票基础信息同步成功",
        "status": "success",
    }
    
    with patch('src.modules.data_engineering.application.services.basic_data_sync_service.SyncUseCaseFactory') as mock_factory_class:
        mock_use_case = MagicMock()
        mock_use_case.__aenter__ = AsyncMock(return_value=mock_use_case)
        mock_use_case.execute = AsyncMock(return_value=mock_use_case_result)
        mock_factory_class.create_sync_stock_basic_use_case.return_value = mock_use_case
        
        # 执行测试
        result = await service.run_stock_basic_sync()
        
        # 验证结果
        assert result == expected_result
        
        # 验证用例被执行
        mock_use_case.execute.assert_called_once()


@pytest.mark.asyncio
async def test_run_stock_basic_sync_failure(
    mock_async_session_local,
    mock_execution_tracker,
):
    """测试股票基础信息同步失败场景。"""
    
    service = BasicDataSyncService()
    
    # 模拟失败的用例执行结果
    mock_use_case_result = MagicMock()
    mock_use_case_result.synced_count = 0
    mock_use_case_result.message = "股票基础信息同步失败：API 限流"
    mock_use_case_result.status = "failed"
    
    # 预期的返回结果
    expected_result = {
        "synced_count": 0,
        "message": "股票基础信息同步失败：API 限流",
        "status": "failed",
    }
    
    with patch('src.modules.data_engineering.application.services.basic_data_sync_service.SyncUseCaseFactory') as mock_factory_class:
        mock_use_case = MagicMock()
        mock_use_case.__aenter__ = AsyncMock(return_value=mock_use_case)
        mock_use_case.execute = AsyncMock(return_value=mock_use_case_result)
        mock_factory_class.create_sync_stock_basic_use_case.return_value = mock_use_case
        
        # 执行测试
        result = await service.run_stock_basic_sync()
        
        # 验证失败结果
        assert result == expected_result
        assert result["synced_count"] == 0
        assert result["status"] == "failed"
        assert "API 限流" in result["message"]


@pytest.mark.asyncio
async def test_run_stock_basic_sync_exception_handling(
    mock_async_session_local,
    mock_execution_tracker,
):
    """测试股票基础信息同步异常处理。"""
    
    service = BasicDataSyncService()
    
    with patch('src.modules.data_engineering.application.services.basic_data_sync_service.SyncUseCaseFactory') as mock_factory_class:
        mock_use_case = MagicMock()
        mock_use_case.__aenter__ = AsyncMock(return_value=mock_use_case)
        mock_use_case.execute = AsyncMock(side_effect=ValueError("无效的股票代码格式"))
        mock_factory_class.create_sync_stock_basic_use_case.return_value = mock_use_case
        
        # 验证异常被正确传播
        with pytest.raises(ValueError, match="无效的股票代码格式"):
            await service.run_stock_basic_sync()
        
        # 验证用例被执行
        mock_use_case.execute.assert_called_once()


@pytest.mark.asyncio
async def test_run_stock_basic_sync_tracking_integration(
    mock_async_session_local,
    mock_execution_tracker,
):
    """测试股票基础信息同步与追踪系统的集成。"""
    
    service = BasicDataSyncService()
    
    mock_use_case_result = MagicMock()
    mock_use_case_result.synced_count = 1000
    mock_use_case_result.message = "同步成功"
    mock_use_case_result.status = "success"
    
    with patch('src.modules.data_engineering.application.services.basic_data_sync_service.SyncUseCaseFactory') as mock_factory_class:
        mock_use_case = MagicMock()
        mock_use_case.__aenter__ = AsyncMock(return_value=mock_use_case)
        mock_use_case.execute = AsyncMock(return_value=mock_use_case_result)
        mock_factory_class.create_sync_stock_basic_use_case.return_value = mock_use_case
        
        # 执行测试
        result = await service.run_stock_basic_sync()
        
        # 验证结果
        assert result["synced_count"] == 1000
        
        # 验证 ExecutionTracker 被正确调用
        mock_execution_tracker.assert_called_once()
        call_kwargs = mock_execution_tracker.call_args[1]
        assert call_kwargs['job_id'] == "sync_stock_basic"


@pytest.mark.asyncio
async def test_run_stock_basic_sync_result_transformation(
    mock_async_session_local,
    mock_execution_tracker,
):
    """测试股票基础信息同步结果转换。"""
    
    service = BasicDataSyncService()
    
    # 模拟复杂的用例执行结果
    mock_use_case_result = MagicMock()
    mock_use_case_result.synced_count = 3500
    mock_use_case_result.message = "同步完成，包含新增和更新记录"
    mock_use_case_result.status = "success"
    mock_use_case_result.new_count = 100
    mock_use_case_result.updated_count = 3400
    mock_use_case_result.skipped_count = 5
    
    expected_result = {
        "synced_count": 3500,
        "message": "同步完成，包含新增和更新记录",
        "status": "success",
    }
    
    with patch('src.modules.data_engineering.application.services.basic_data_sync_service.SyncUseCaseFactory') as mock_factory_class:
        mock_use_case = MagicMock()
        mock_use_case.__aenter__ = AsyncMock(return_value=mock_use_case)
        mock_use_case.execute = AsyncMock(return_value=mock_use_case_result)
        mock_factory_class.create_sync_stock_basic_use_case.return_value = mock_use_case
        
        # 执行测试
        result = await service.run_stock_basic_sync()
        
        # 验证结果转换正确（只提取需要的字段）
        assert result == expected_result
        assert "synced_count" in result
        assert "message" in result
        assert "status" in result
        # 确保其他字段没有被包含
        assert "new_count" not in result
        assert "updated_count" not in result


# =============================================================================
# 集成测试
# =============================================================================

@pytest.mark.asyncio
async def test_basic_data_sync_service_integration(
    mock_async_session_local,
    mock_execution_tracker,
):
    """测试 BasicDataSyncService 的集成功能。"""
    
    service = BasicDataSyncService()
    
    # 测试两个方法都能正常工作
    # 1. 概念同步
    concept_result = MagicMock(spec=ConceptSyncResult)
    concept_result.total_concepts = 100
    concept_result.success_concepts = 95
    concept_result.failed_concepts = 5
    concept_result.total_stocks = 2000
    concept_result.elapsed_time = 80.0
    
    with patch('src.modules.data_engineering.application.services.basic_data_sync_service.DataEngineeringContainer') as mock_container_class:
        with patch('src.modules.data_engineering.application.services.basic_data_sync_service.SyncConceptDataCmd') as mock_cmd_class:
            mock_container = MagicMock()
            mock_container.concept_provider.return_value = MagicMock()
            mock_container.concept_repository.return_value = MagicMock()
            mock_container_class.return_value = mock_container
            
            mock_sync_cmd = MagicMock()
            mock_sync_cmd.execute = AsyncMock(return_value=concept_result)
            mock_cmd_class.return_value = mock_sync_cmd
            
            result1 = await service.run_concept_sync()
            assert result1 == concept_result
            
            # 2. 股票基础信息同步
            stock_use_case_result = MagicMock()
            stock_use_case_result.synced_count = 4000
            stock_use_case_result.message = "股票基础信息同步成功"
            stock_use_case_result.status = "success"
            
            with patch('src.modules.data_engineering.application.services.basic_data_sync_service.SyncUseCaseFactory') as mock_factory_class:
                mock_use_case = MagicMock()
                mock_use_case.__aenter__ = AsyncMock(return_value=mock_use_case)
                mock_use_case.execute = AsyncMock(return_value=stock_use_case_result)
                mock_factory_class.create_sync_stock_basic_use_case.return_value = mock_use_case
                
                result2 = await service.run_stock_basic_sync()
                assert result2["synced_count"] == 4000
                
                # 验证两个方法都使用了追踪系统
                assert mock_execution_tracker.call_count == 2


# =============================================================================
# 边界条件测试
# =============================================================================

@pytest.mark.asyncio
async def test_run_concept_sync_empty_result(
    mock_async_session_local,
    mock_execution_tracker,
):
    """测试空概念结果的处理。"""
    
    service = BasicDataSyncService()
    
    # 模拟空结果
    expected_result = MagicMock(spec=ConceptSyncResult)
    expected_result.total_concepts = 0
    expected_result.success_concepts = 0
    expected_result.failed_concepts = 0
    expected_result.total_stocks = 0
    expected_result.elapsed_time = 0.0
    
    with patch('src.modules.data_engineering.application.services.basic_data_sync_service.DataEngineeringContainer') as mock_container_class:
        with patch('src.modules.data_engineering.application.services.basic_data_sync_service.SyncConceptDataCmd') as mock_cmd_class:
            mock_container = MagicMock()
            mock_container.concept_provider.return_value = MagicMock()
            mock_container.concept_repository.return_value = MagicMock()
            mock_container_class.return_value = mock_container
            
            mock_sync_cmd = MagicMock()
            mock_sync_cmd.execute = AsyncMock(return_value=expected_result)
            mock_cmd_class.return_value = mock_sync_cmd
            
            # 执行测试
            result = await service.run_concept_sync()
            
            # 验证空结果被正确处理
            assert result == expected_result
            assert result.total_concepts == 0
            assert result.success_concepts == 0


@pytest.mark.asyncio
async def test_run_stock_basic_sync_empty_result(
    mock_async_session_local,
    mock_execution_tracker,
):
    """测试空股票基础信息结果的处理。"""
    
    service = BasicDataSyncService()
    
    # 模拟空结果
    mock_use_case_result = MagicMock()
    mock_use_case_result.synced_count = 0
    mock_use_case_result.message = "没有需要同步的股票基础信息"
    mock_use_case_result.status = "success"
    
    expected_result = {
        "synced_count": 0,
        "message": "没有需要同步的股票基础信息",
        "status": "success",
    }
    
    with patch('src.modules.data_engineering.application.services.basic_data_sync_service.SyncUseCaseFactory') as mock_factory_class:
        mock_use_case = MagicMock()
        mock_use_case.__aenter__ = AsyncMock(return_value=mock_use_case)
        mock_use_case.execute = AsyncMock(return_value=mock_use_case_result)
        mock_factory_class.create_sync_stock_basic_use_case.return_value = mock_use_case
        
        # 执行测试
        result = await service.run_stock_basic_sync()
        
        # 验证空结果被正确处理
        assert result == expected_result
        assert result["synced_count"] == 0
        assert result["status"] == "success"
