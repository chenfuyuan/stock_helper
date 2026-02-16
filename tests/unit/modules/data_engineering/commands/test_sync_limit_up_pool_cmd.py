"""SyncLimitUpPoolCmd 单元测试。"""

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.modules.data_engineering.application.commands.sync_limit_up_pool_cmd import (
    SyncLimitUpPoolCmd,
)
from src.modules.data_engineering.domain.model.limit_up_pool import LimitUpPoolStock


@pytest.fixture
def mock_sentiment_provider():
    """Mock 市场情绪数据提供方。"""
    return AsyncMock()


@pytest.fixture
def mock_limit_up_pool_repo():
    """Mock 涨停池仓储。"""
    return AsyncMock()


@pytest.fixture
def sync_cmd(mock_sentiment_provider, mock_limit_up_pool_repo):
    """创建 SyncLimitUpPoolCmd 实例。"""
    return SyncLimitUpPoolCmd(mock_sentiment_provider, mock_limit_up_pool_repo)


@pytest.mark.asyncio
async def test_execute_success(sync_cmd, mock_sentiment_provider, mock_limit_up_pool_repo):
    """测试：成功同步涨停池数据。"""
    # Arrange
    trade_date = date(2024, 1, 15)
    mock_dto = MagicMock(
        third_code="000001.SZ",
        stock_name="测试股票",
        pct_chg=10.0,
        close=20.0,
        amount=100000.0,
        turnover_rate=5.0,
        consecutive_boards=1,
        first_limit_up_time="09:30:00",
        last_limit_up_time="09:30:00",
        industry="测试行业",
    )
    mock_sentiment_provider.fetch_limit_up_pool.return_value = [mock_dto]
    mock_limit_up_pool_repo.save_all.return_value = 1

    # Act
    result = await sync_cmd.execute(trade_date)

    # Assert
    assert result == 1
    mock_sentiment_provider.fetch_limit_up_pool.assert_called_once_with(trade_date)
    mock_limit_up_pool_repo.save_all.assert_called_once()


@pytest.mark.asyncio
async def test_execute_empty_data(sync_cmd, mock_sentiment_provider, mock_limit_up_pool_repo):
    """测试：Provider 返回空数据。"""
    # Arrange
    trade_date = date(2024, 1, 15)
    mock_sentiment_provider.fetch_limit_up_pool.return_value = []

    # Act
    result = await sync_cmd.execute(trade_date)

    # Assert
    assert result == 0
    mock_limit_up_pool_repo.save_all.assert_not_called()


@pytest.mark.asyncio
async def test_execute_provider_error(sync_cmd, mock_sentiment_provider):
    """测试：Provider 抛出异常时正确传播。"""
    # Arrange
    trade_date = date(2024, 1, 15)
    mock_sentiment_provider.fetch_limit_up_pool.side_effect = Exception("Provider 错误")

    # Act & Assert
    with pytest.raises(Exception, match="Provider 错误"):
        await sync_cmd.execute(trade_date)
