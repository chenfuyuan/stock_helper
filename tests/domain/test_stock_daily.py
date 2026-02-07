import pytest
from app.domain.stock.entities import StockDaily
from datetime import date

def test_stock_daily_creation():
    """测试 StockDaily 实体创建"""
    daily = StockDaily(
        third_code="000001.SZ",
        trade_date=date(2023, 1, 1),
        open=10.0,
        high=10.5,
        low=9.5,
        close=10.2,
        pre_close=10.0,
        change=0.2,
        pct_chg=2.0,
        vol=1000.0,
        amount=10000.0,
        source="tushare"
    )
    
    assert daily.third_code == "000001.SZ"
    assert daily.trade_date == date(2023, 1, 1)
    assert daily.open == 10.0
    assert daily.source == "tushare"

def test_stock_daily_validation():
    """测试 StockDaily 必填字段验证"""
    with pytest.raises(ValueError):
        StockDaily(
            third_code="000001.SZ",
            # trade_date is missing
            open=10.0,
            high=10.5,
            low=9.5,
            close=10.2,
            pre_close=10.0,
            change=0.2,
            pct_chg=2.0,
            vol=1000.0,
            amount=10000.0
        )
