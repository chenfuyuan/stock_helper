"""
ConceptHeatCalculator 领域服务单元测试
验证等权平均计算、涨停统计、停牌过滤、全停牌排除逻辑
"""

from datetime import date

import pytest

from src.modules.market_insight.domain.dtos.insight_dtos import (
    ConceptStockDTO,
    ConceptWithStocksDTO,
    StockDailyDTO,
)
from src.modules.market_insight.domain.services.concept_heat_calculator import (
    ConceptHeatCalculator,
)


def test_calculate_normal_concept_heat():
    """正常计算板块热度：等权平均、涨停统计"""
    calculator = ConceptHeatCalculator()

    concept_a = ConceptWithStocksDTO(
        code="BK0001",
        name="概念A",
        stocks=[
            ConceptStockDTO(third_code="000001.SZ", stock_name="股票1"),
            ConceptStockDTO(third_code="000002.SZ", stock_name="股票2"),
            ConceptStockDTO(third_code="000003.SZ", stock_name="股票3"),
            ConceptStockDTO(third_code="000004.SZ", stock_name="股票4"),
            ConceptStockDTO(third_code="000005.SZ", stock_name="股票5"),
        ],
    )

    daily_bars = {
        "000001.SZ": StockDailyDTO(
            third_code="000001.SZ",
            stock_name="股票1",
            trade_date=date(2025, 1, 6),
            close=10.0,
            pct_chg=3.0,
            amount=1000000.0,
        ),
        "000002.SZ": StockDailyDTO(
            third_code="000002.SZ",
            stock_name="股票2",
            trade_date=date(2025, 1, 6),
            close=20.0,
            pct_chg=1.5,
            amount=2000000.0,
        ),
        "000003.SZ": StockDailyDTO(
            third_code="000003.SZ",
            stock_name="股票3",
            trade_date=date(2025, 1, 6),
            close=15.0,
            pct_chg=-0.5,
            amount=1500000.0,
        ),
        "000004.SZ": StockDailyDTO(
            third_code="000004.SZ",
            stock_name="股票4",
            trade_date=date(2025, 1, 6),
            close=30.0,
            pct_chg=10.0,
            amount=3000000.0,
        ),
    }

    results = calculator.calculate([concept_a], daily_bars)

    assert len(results) == 1
    heat = results[0]

    assert heat.concept_code == "BK0001"
    assert heat.concept_name == "概念A"
    assert heat.avg_pct_chg == pytest.approx((3.0 + 1.5 + (-0.5) + 10.0) / 4)
    assert heat.avg_pct_chg == pytest.approx(3.5)
    assert heat.stock_count == 4
    assert heat.up_count == 3
    assert heat.down_count == 1


def test_calculate_excludes_fully_suspended_concept():
    """全停牌概念被排除，不生成 ConceptHeat 记录"""
    calculator = ConceptHeatCalculator()

    concept_suspended = ConceptWithStocksDTO(
        code="BK0002",
        name="全停牌概念",
        stocks=[
            ConceptStockDTO(third_code="000010.SZ", stock_name="停牌股1"),
            ConceptStockDTO(third_code="000011.SZ", stock_name="停牌股2"),
        ],
    )

    daily_bars = {
        "000001.SZ": StockDailyDTO(
            third_code="000001.SZ",
            stock_name="其他股票",
            trade_date=date(2025, 1, 6),
            close=10.0,
            pct_chg=1.0,
            amount=1000000.0,
        ),
    }

    results = calculator.calculate([concept_suspended], daily_bars)

    assert len(results) == 0


def test_calculate_counts_limit_up_stocks():
    """涨停成分股被正确统计"""
    calculator = ConceptHeatCalculator()

    concept_b = ConceptWithStocksDTO(
        code="BK0003",
        name="概念B",
        stocks=[
            ConceptStockDTO(third_code="600519.SH", stock_name="主板股"),
            ConceptStockDTO(third_code="300750.SZ", stock_name="创业板股"),
        ],
    )

    daily_bars = {
        "600519.SH": StockDailyDTO(
            third_code="600519.SH",
            stock_name="主板股",
            trade_date=date(2025, 1, 6),
            close=1820.0,
            pct_chg=10.01,
            amount=900000000.0,
        ),
        "300750.SZ": StockDailyDTO(
            third_code="300750.SZ",
            stock_name="创业板股",
            trade_date=date(2025, 1, 6),
            close=250.0,
            pct_chg=20.0,
            amount=500000000.0,
        ),
    }

    results = calculator.calculate([concept_b], daily_bars)

    assert len(results) == 1
    heat = results[0]

    assert heat.limit_up_count == 2


def test_calculate_filters_suspended_stocks():
    """停牌股被过滤，仅统计有行情数据的成分股"""
    calculator = ConceptHeatCalculator()

    concept_c = ConceptWithStocksDTO(
        code="BK0004",
        name="概念C",
        stocks=[
            ConceptStockDTO(third_code="000001.SZ", stock_name="正常股1"),
            ConceptStockDTO(third_code="000002.SZ", stock_name="正常股2"),
            ConceptStockDTO(third_code="000099.SZ", stock_name="停牌股"),
        ],
    )

    daily_bars = {
        "000001.SZ": StockDailyDTO(
            third_code="000001.SZ",
            stock_name="正常股1",
            trade_date=date(2025, 1, 6),
            close=10.0,
            pct_chg=2.0,
            amount=1000000.0,
        ),
        "000002.SZ": StockDailyDTO(
            third_code="000002.SZ",
            stock_name="正常股2",
            trade_date=date(2025, 1, 6),
            close=12.0,
            pct_chg=3.0,
            amount=1200000.0,
        ),
    }

    results = calculator.calculate([concept_c], daily_bars)

    assert len(results) == 1
    heat = results[0]

    assert heat.stock_count == 2
    assert heat.avg_pct_chg == pytest.approx((2.0 + 3.0) / 2)
