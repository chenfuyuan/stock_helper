"""DataSyncApplicationService 单元测试（简化版本）。

由于 DataSyncApplicationService 涉及 session 管理、ExecutionTracker、Container 等复杂依赖，
完整的单元测试需要大量 mock。这里提供基础测试覆盖核心逻辑。
"""

import pytest

from src.modules.data_engineering.application.services.data_sync_application_service import (
    DataSyncApplicationService,
)


@pytest.fixture
def service():
    """创建 DataSyncApplicationService 实例。"""
    return DataSyncApplicationService()


def test_service_instantiation(service):
    """测试：服务可以正常实例化（无状态服务）。"""
    assert service is not None
    assert isinstance(service, DataSyncApplicationService)


def test_service_has_required_methods(service):
    """测试：服务具备所有必需方法。"""
    assert hasattr(service, "run_daily_incremental_sync")
    assert hasattr(service, "run_incremental_finance_sync")
    assert hasattr(service, "run_concept_sync")
    assert hasattr(service, "run_akshare_market_data_sync")
    assert hasattr(service, "run_stock_basic_sync")
    assert hasattr(service, "run_daily_history_sync")
    assert hasattr(service, "run_finance_history_sync")


def test_all_methods_are_async(service):
    """测试：所有公共方法都是异步的。"""
    import asyncio
    import inspect

    methods = [
        service.run_daily_incremental_sync,
        service.run_incremental_finance_sync,
        service.run_concept_sync,
        service.run_akshare_market_data_sync,
        service.run_stock_basic_sync,
        service.run_daily_history_sync,
        service.run_finance_history_sync,
    ]

    for method in methods:
        assert asyncio.iscoroutinefunction(method), f"{method.__name__} 应该是异步方法"


# 注：完整的集成测试（调用真实依赖）应在 tests/integration/ 中实现
# 此处仅验证服务的基础结构和方法签名
