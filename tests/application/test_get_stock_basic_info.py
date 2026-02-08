import pytest
from unittest.mock import AsyncMock
from datetime import date
from app.application.stock.use_cases import GetStockBasicInfoUseCase
from app.domain.stock.entities import StockInfo, StockDaily
from app.domain.stock.enums import MarketType, ListStatus

@pytest.mark.asyncio
class TestGetStockBasicInfoUseCase:
    
    async def test_execute_success(self):
        """测试成功获取股票基础信息和最新行情"""
        # 1. Mock Data
        symbol = "000001"
        third_code = "000001.SZ"
        
        mock_info = StockInfo(
            symbol=symbol,
            third_code=third_code,
            name="平安银行",
            market=MarketType.MAIN,
            list_status=ListStatus.LISTED,
            list_date=date(1991, 4, 3)
        )
        
        mock_daily = StockDaily(
            third_code=third_code,
            trade_date=date(2023, 1, 1),
            open=10.0,
            high=10.5,
            low=9.5,
            close=10.2,
            pre_close=10.0,
            change=0.2,
            pct_chg=2.0,
            vol=10000,
            amount=100000
        )
        
        # 2. Mock Repositories
        mock_stock_repo = AsyncMock()
        mock_stock_repo.get_by_symbol.return_value = mock_info
        
        mock_daily_repo = AsyncMock()
        mock_daily_repo.get_latest_by_third_code.return_value = mock_daily
        
        # 3. Execute Use Case
        use_case = GetStockBasicInfoUseCase(mock_stock_repo, mock_daily_repo)
        result = await use_case.execute(symbol)
        
        # 4. Assertions
        assert result is not None
        assert result.info.symbol == symbol
        assert result.info.name == "平安银行"
        assert result.daily is not None
        assert result.daily.close == 10.2
        
        # Verify repo calls
        mock_stock_repo.get_by_symbol.assert_called_once_with(symbol)
        mock_daily_repo.get_latest_by_third_code.assert_called_once_with(third_code)

    async def test_execute_not_found(self):
        """测试股票不存在的情况"""
        symbol = "999999"
        
        mock_stock_repo = AsyncMock()
        mock_stock_repo.get_by_symbol.return_value = None
        
        mock_daily_repo = AsyncMock()
        
        use_case = GetStockBasicInfoUseCase(mock_stock_repo, mock_daily_repo)
        result = await use_case.execute(symbol)
        
        assert result is None
        mock_stock_repo.get_by_symbol.assert_called_once_with(symbol)
        mock_daily_repo.get_latest_by_third_code.assert_not_called()

    async def test_execute_no_daily_data(self):
        """测试只有基础信息没有行情的情况"""
        symbol = "000001"
        third_code = "000001.SZ"
        
        mock_info = StockInfo(
            symbol=symbol,
            third_code=third_code,
            name="平安银行",
            market=MarketType.MAIN,
            list_status=ListStatus.LISTED,
            list_date=date(1991, 4, 3)
        )
        
        mock_stock_repo = AsyncMock()
        mock_stock_repo.get_by_symbol.return_value = mock_info
        
        mock_daily_repo = AsyncMock()
        mock_daily_repo.get_latest_by_third_code.return_value = None
        
        use_case = GetStockBasicInfoUseCase(mock_stock_repo, mock_daily_repo)
        result = await use_case.execute(symbol)
        
        assert result is not None
        assert result.info.symbol == symbol
        assert result.daily is None
