from datetime import date

import pytest

from src.modules.data_engineering.domain.model.stock import StockInfo


def test_stock_info_creation():
    """测试 StockInfo 实体创建"""
    stock = StockInfo(
        third_code="000001.SZ",
        symbol="000001",
        name="平安银行",
        area="深圳",
        industry="银行",
        market="主板",
        list_date=date(1991, 4, 3),
    )

    assert stock.third_code == "000001.SZ"
    assert stock.symbol == "000001"
    assert stock.name == "平安银行"
    assert stock.list_date.year == 1991


def test_stock_info_validation():
    """测试 StockInfo 必填字段验证"""
    with pytest.raises(ValueError):
        StockInfo(
            third_code="000001.SZ",
            symbol="000001",
            # name is missing
        )
