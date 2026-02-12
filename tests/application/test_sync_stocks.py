import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from src.modules.data_engineering.application.commands.sync_stock_list_cmd import SyncStocksUseCase
from src.modules.data_engineering.domain.model.stock import StockInfo

@pytest.mark.asyncio
async def test_sync_stocks_use_case():
    """测试股票同步用例"""
    mock_repo = AsyncMock()
    mock_repo.save_all.return_value = [
        StockInfo(third_code="000001.SZ", symbol="000001", name="Test Stock")
    ]
    mock_provider = AsyncMock()
    mock_provider.fetch_stock_basic.return_value = [
        StockInfo(third_code="000001.SZ", symbol="000001", name="Test Stock")
    ]
    use_case = SyncStocksUseCase(mock_repo, mock_provider)
    result = await use_case.execute()
    assert result["status"] == "success"
    assert result["synced_count"] == 1
    
    # Verify calls
    mock_provider.fetch_stock_basic.assert_called_once()
    mock_repo.save_all.assert_called_once()

@pytest.mark.asyncio
async def test_sync_stocks_empty():
    """测试无数据情况"""
    mock_repo = AsyncMock()
    
    mock_provider = AsyncMock()
    mock_provider.fetch_stock_basic.return_value = []
    
    use_case = SyncStocksUseCase(mock_repo, mock_provider)
    result = await use_case.execute()
    
    assert result["status"] == "success"
    assert result["synced_count"] == 0
    mock_repo.save_all.assert_not_called()
