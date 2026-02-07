import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from app.application.stock.use_cases import SyncStocksUseCase
from app.domain.stock.entities import StockInfo
from datetime import date

@pytest.mark.asyncio
async def test_sync_stocks_use_case():
    """测试股票同步用例"""
    
    # Mock Repository
    mock_repo = AsyncMock()
    mock_repo.save_all.return_value = [
        StockInfo(third_code="000001.SZ", symbol="000001", name="Test Stock")
    ]
    
    # Mock TushareService
    mock_tushare_service = AsyncMock()
    mock_tushare_service.fetch_stock_basic.return_value = [
        StockInfo(third_code="000001.SZ", symbol="000001", name="Test Stock")
    ]
    
    with patch("app.application.stock.use_cases.TushareService", return_value=mock_tushare_service):
        use_case = SyncStocksUseCase(mock_repo)
        result = await use_case.execute()
        
        assert result["status"] == "success"
        assert result["synced_count"] == 1
        
        # Verify calls
        mock_tushare_service.fetch_stock_basic.assert_called_once()
        mock_repo.save_all.assert_called_once()

@pytest.mark.asyncio
async def test_sync_stocks_empty():
    """测试无数据情况"""
    mock_repo = AsyncMock()
    
    mock_tushare_service = AsyncMock()
    mock_tushare_service.fetch_stock_basic.return_value = []
    
    with patch("app.application.stock.use_cases.TushareService", return_value=mock_tushare_service):
        use_case = SyncStocksUseCase(mock_repo)
        result = await use_case.execute()
        
        assert result["status"] == "success"
        assert result["synced_count"] == 0
        mock_repo.save_all.assert_not_called()
