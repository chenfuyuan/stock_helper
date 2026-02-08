import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from src.modules.market_data.application.use_cases import SyncStocksUseCase
from src.modules.market_data.domain.entities import StockInfo
from src.modules.market_data.application.dtos import SyncStockOutput

@pytest.mark.asyncio
async def test_sync_stocks_use_case():
    """测试股票同步用例"""
    
    # Mock Repository
    mock_repo = AsyncMock()
    # 注意：save_all 应该返回 List[StockInfo]
    mock_repo.save_all.return_value = [
        StockInfo(third_code="000001.SZ", symbol="000001", name="Test Stock")
    ]
    
    # Mock StockDataProvider (不一定是 TushareService，接口层 Mock 即可)
    mock_provider = AsyncMock()
    mock_provider.fetch_stock_basic.return_value = [
        StockInfo(third_code="000001.SZ", symbol="000001", name="Test Stock")
    ]
    
    # 注入 Mock 对象
    use_case = SyncStocksUseCase(mock_repo, mock_provider)
    result = await use_case.execute()
    
    assert isinstance(result, SyncStockOutput)
    assert result.status == "success"
    assert result.synced_count == 1
    
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
    
    assert isinstance(result, SyncStockOutput)
    assert result.status == "success"
    assert result.synced_count == 0
    mock_repo.save_all.assert_not_called()
