"""SyncAkShareMarketDataCmd 单元测试（编排入口）。"""

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.modules.data_engineering.application.commands.sync_akshare_market_data_cmd import (
    SyncAkShareMarketDataCmd,
)


@pytest.fixture
def mock_providers_and_repos():
    """Mock 所有 Provider 和 Repository。"""
    return {
        "sentiment_provider": AsyncMock(),
        "dragon_tiger_provider": AsyncMock(),
        "capital_flow_provider": AsyncMock(),
        "limit_up_pool_repo": AsyncMock(),
        "broken_board_repo": AsyncMock(),
        "previous_limit_up_repo": AsyncMock(),
        "dragon_tiger_repo": AsyncMock(),
        "sector_capital_flow_repo": AsyncMock(),
    }


@pytest.fixture
def sync_cmd(mock_providers_and_repos):
    """创建 SyncAkShareMarketDataCmd 实例。"""
    return SyncAkShareMarketDataCmd(**mock_providers_and_repos)


@pytest.mark.asyncio
async def test_execute_all_success(sync_cmd):
    """测试：所有子 Command 成功执行。"""
    # Arrange
    trade_date = date(2024, 1, 15)
    
    # Mock 所有子 Command 的 execute 方法
    sync_cmd.limit_up_cmd.execute = AsyncMock(return_value=10)
    sync_cmd.broken_board_cmd.execute = AsyncMock(return_value=5)
    sync_cmd.previous_limit_up_cmd.execute = AsyncMock(return_value=8)
    sync_cmd.dragon_tiger_cmd.execute = AsyncMock(return_value=3)
    sync_cmd.sector_capital_flow_cmd.execute = AsyncMock(return_value=20)

    # Act
    result = await sync_cmd.execute(trade_date)

    # Assert
    assert result.trade_date == trade_date
    assert result.limit_up_pool_count == 10
    assert result.broken_board_count == 5
    assert result.previous_limit_up_count == 8
    assert result.dragon_tiger_count == 3
    assert result.sector_capital_flow_count == 20
    assert len(result.errors) == 0


@pytest.mark.asyncio
async def test_execute_error_isolation(sync_cmd):
    """测试：错误隔离——某子 Command 失败不中断其他。"""
    # Arrange
    trade_date = date(2024, 1, 15)
    
    # Mock：涨停池和龙虎榜失败，其他成功
    sync_cmd.limit_up_cmd.execute = AsyncMock(side_effect=Exception("涨停池失败"))
    sync_cmd.broken_board_cmd.execute = AsyncMock(return_value=5)
    sync_cmd.previous_limit_up_cmd.execute = AsyncMock(return_value=8)
    sync_cmd.dragon_tiger_cmd.execute = AsyncMock(side_effect=Exception("龙虎榜失败"))
    sync_cmd.sector_capital_flow_cmd.execute = AsyncMock(return_value=20)

    # Act
    result = await sync_cmd.execute(trade_date)

    # Assert
    assert result.trade_date == trade_date
    assert result.limit_up_pool_count == 0  # 失败时为 0
    assert result.broken_board_count == 5
    assert result.previous_limit_up_count == 8
    assert result.dragon_tiger_count == 0  # 失败时为 0
    assert result.sector_capital_flow_count == 20
    assert len(result.errors) == 2
    assert "涨停池数据同步失败" in result.errors[0]
    assert "龙虎榜数据同步失败" in result.errors[1]


@pytest.mark.asyncio
async def test_execute_all_failed(sync_cmd):
    """测试：所有子 Command 失败仍能返回结果。"""
    # Arrange
    trade_date = date(2024, 1, 15)
    
    # Mock：所有失败
    sync_cmd.limit_up_cmd.execute = AsyncMock(side_effect=Exception("失败1"))
    sync_cmd.broken_board_cmd.execute = AsyncMock(side_effect=Exception("失败2"))
    sync_cmd.previous_limit_up_cmd.execute = AsyncMock(side_effect=Exception("失败3"))
    sync_cmd.dragon_tiger_cmd.execute = AsyncMock(side_effect=Exception("失败4"))
    sync_cmd.sector_capital_flow_cmd.execute = AsyncMock(side_effect=Exception("失败5"))

    # Act
    result = await sync_cmd.execute(trade_date)

    # Assert
    assert result.trade_date == trade_date
    assert result.limit_up_pool_count == 0
    assert result.broken_board_count == 0
    assert result.previous_limit_up_count == 0
    assert result.dragon_tiger_count == 0
    assert result.sector_capital_flow_count == 0
    assert len(result.errors) == 5
