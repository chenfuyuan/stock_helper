"""
LimitUpScanner 领域服务单元测试
验证各板块涨停识别、未达阈值、概念归因、无概念归属逻辑
"""

from datetime import date

import pytest

from src.modules.market_insight.domain.dtos.insight_dtos import (
    ConceptInfoDTO,
    StockDailyDTO,
)
from src.modules.market_insight.domain.model.enums import LimitType
from src.modules.market_insight.domain.services.limit_up_scanner import LimitUpScanner


def test_scan_main_board_limit_up():
    """主板股票涨停识别"""
    scanner = LimitUpScanner()

    daily_bars = [
        StockDailyDTO(
            third_code="600519.SH",
            stock_name="贵州茅台",
            trade_date=date(2025, 1, 6),
            close=1820.0,
            pct_chg=10.01,
            amount=900000000.0,
        ),
    ]

    concept_stock_map = {}

    results = scanner.scan(daily_bars, concept_stock_map)

    assert len(results) == 1
    assert results[0].third_code == "600519.SH"
    assert results[0].limit_type == LimitType.MAIN_BOARD
    assert results[0].pct_chg == 10.01


def test_scan_gem_limit_up():
    """创业板股票涨停识别"""
    scanner = LimitUpScanner()

    daily_bars = [
        StockDailyDTO(
            third_code="300750.SZ",
            stock_name="宁德时代",
            trade_date=date(2025, 1, 6),
            close=250.0,
            pct_chg=20.0,
            amount=500000000.0,
        ),
    ]

    concept_stock_map = {}

    results = scanner.scan(daily_bars, concept_stock_map)

    assert len(results) == 1
    assert results[0].third_code == "300750.SZ"
    assert results[0].limit_type == LimitType.GEM


def test_scan_star_limit_up():
    """科创板股票涨停识别"""
    scanner = LimitUpScanner()

    daily_bars = [
        StockDailyDTO(
            third_code="688001.SH",
            stock_name="华兴源创",
            trade_date=date(2025, 1, 6),
            close=30.0,
            pct_chg=19.9,
            amount=100000000.0,
        ),
    ]

    concept_stock_map = {}

    results = scanner.scan(daily_bars, concept_stock_map)

    assert len(results) == 1
    assert results[0].third_code == "688001.SH"
    assert results[0].limit_type == LimitType.STAR


def test_scan_st_stock_limit_up():
    """ST 股票涨停识别"""
    scanner = LimitUpScanner()

    daily_bars = [
        StockDailyDTO(
            third_code="000007.SZ",
            stock_name="*ST全新",
            trade_date=date(2025, 1, 6),
            close=5.0,
            pct_chg=5.0,
            amount=50000000.0,
        ),
    ]

    concept_stock_map = {}

    results = scanner.scan(daily_bars, concept_stock_map)

    assert len(results) == 1
    assert results[0].third_code == "000007.SZ"
    assert results[0].limit_type == LimitType.ST


def test_scan_bse_limit_up():
    """北交所股票涨停识别"""
    scanner = LimitUpScanner()

    daily_bars = [
        StockDailyDTO(
            third_code="430047.BJ",
            stock_name="诺思兰德",
            trade_date=date(2025, 1, 6),
            close=50.0,
            pct_chg=30.0,
            amount=20000000.0,
        ),
    ]

    concept_stock_map = {}

    results = scanner.scan(daily_bars, concept_stock_map)

    assert len(results) == 1
    assert results[0].third_code == "430047.BJ"
    assert results[0].limit_type == LimitType.BSE


def test_scan_not_limit_up_below_threshold():
    """未达涨停阈值不识别"""
    scanner = LimitUpScanner()

    daily_bars = [
        StockDailyDTO(
            third_code="600000.SH",
            stock_name="浦发银行",
            trade_date=date(2025, 1, 6),
            close=8.5,
            pct_chg=9.5,
            amount=100000000.0,
        ),
    ]

    concept_stock_map = {}

    results = scanner.scan(daily_bars, concept_stock_map)

    assert len(results) == 0


def test_scan_with_concept_attribution():
    """涨停股映射概念归因"""
    scanner = LimitUpScanner()

    daily_bars = [
        StockDailyDTO(
            third_code="000001.SZ",
            stock_name="平安银行",
            trade_date=date(2025, 1, 6),
            close=12.0,
            pct_chg=10.0,
            amount=200000000.0,
        ),
    ]

    concept_stock_map = {
        "000001.SZ": [
            ConceptInfoDTO(code="BK0001", name="金融概念"),
            ConceptInfoDTO(code="BK0002", name="深圳本地"),
        ],
    }

    results = scanner.scan(daily_bars, concept_stock_map)

    assert len(results) == 1
    assert results[0].third_code == "000001.SZ"
    assert results[0].concept_codes == ["BK0001", "BK0002"]
    assert results[0].concept_names == ["金融概念", "深圳本地"]


def test_scan_no_concept_attribution():
    """涨停股无概念归属"""
    scanner = LimitUpScanner()

    daily_bars = [
        StockDailyDTO(
            third_code="000001.SZ",
            stock_name="平安银行",
            trade_date=date(2025, 1, 6),
            close=12.0,
            pct_chg=10.0,
            amount=200000000.0,
        ),
    ]

    concept_stock_map = {}

    results = scanner.scan(daily_bars, concept_stock_map)

    assert len(results) == 1
    assert results[0].third_code == "000001.SZ"
    assert results[0].concept_codes == []
    assert results[0].concept_names == []
