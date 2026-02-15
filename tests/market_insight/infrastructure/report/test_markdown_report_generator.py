"""
MarkdownReportGenerator 单元测试
验证正常报告生成、无涨停场景、文件覆盖逻辑
"""

import os
import tempfile
from datetime import date

import pytest

from src.modules.market_insight.domain.model.concept_heat import ConceptHeat
from src.modules.market_insight.domain.model.enums import LimitType
from src.modules.market_insight.domain.model.limit_up_stock import LimitUpStock
from src.modules.market_insight.infrastructure.report.markdown_report_generator import (
    MarkdownReportGenerator,
)


def test_generate_normal_report():
    """正常生成报告"""
    with tempfile.TemporaryDirectory() as tmpdir:
        generator = MarkdownReportGenerator(output_dir=tmpdir)

        concept_heats = [
            ConceptHeat(
                trade_date=date(2025, 1, 6),
                concept_code="BK0001",
                concept_name="人工智能",
                avg_pct_chg=5.5,
                stock_count=50,
                up_count=45,
                down_count=5,
                limit_up_count=10,
                total_amount=5000000000.0,
            ),
            ConceptHeat(
                trade_date=date(2025, 1, 6),
                concept_code="BK0002",
                concept_name="新能源",
                avg_pct_chg=3.2,
                stock_count=80,
                up_count=60,
                down_count=20,
                limit_up_count=5,
                total_amount=8000000000.0,
            ),
        ]

        limit_up_stocks = [
            LimitUpStock(
                trade_date=date(2025, 1, 6),
                third_code="000001.SZ",
                stock_name="股票A",
                pct_chg=10.0,
                close=12.0,
                amount=200000000.0,
                concept_codes=["BK0001"],
                concept_names=["人工智能"],
                limit_type=LimitType.MAIN_BOARD,
            ),
        ]

        report_path = generator.generate(concept_heats, limit_up_stocks, top_n=10)

        assert os.path.exists(report_path)
        assert report_path.endswith("2025-01-06-market-insight.md")

        with open(report_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert "# 每日市场洞察 - 2025-01-06" in content
        assert "人工智能" in content
        assert "新能源" in content
        assert "股票A" in content


def test_generate_report_with_no_limit_up():
    """无涨停场景"""
    with tempfile.TemporaryDirectory() as tmpdir:
        generator = MarkdownReportGenerator(output_dir=tmpdir)

        concept_heats = [
            ConceptHeat(
                trade_date=date(2025, 1, 6),
                concept_code="BK0001",
                concept_name="人工智能",
                avg_pct_chg=2.5,
                stock_count=50,
                up_count=30,
                down_count=20,
                limit_up_count=0,
                total_amount=3000000000.0,
            ),
        ]

        limit_up_stocks = []

        report_path = generator.generate(concept_heats, limit_up_stocks, top_n=10)

        assert os.path.exists(report_path)

        with open(report_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert "今日无涨停" in content
        assert "涨停总数**: 0 只" in content


def test_generate_report_overwrites_existing():
    """报告文件可覆盖"""
    with tempfile.TemporaryDirectory() as tmpdir:
        generator = MarkdownReportGenerator(output_dir=tmpdir)

        concept_heats = [
            ConceptHeat(
                trade_date=date(2025, 1, 6),
                concept_code="BK0001",
                concept_name="人工智能",
                avg_pct_chg=5.5,
                stock_count=50,
                up_count=45,
                down_count=5,
                limit_up_count=10,
                total_amount=5000000000.0,
            ),
        ]

        limit_up_stocks = []

        # 第一次生成
        report_path_1 = generator.generate(concept_heats, limit_up_stocks, top_n=10)

        with open(report_path_1, "r", encoding="utf-8") as f:
            content_1 = f.read()

        # 第二次生成（同一日期）
        report_path_2 = generator.generate(concept_heats, limit_up_stocks, top_n=10)

        assert report_path_1 == report_path_2
        assert os.path.exists(report_path_2)

        with open(report_path_2, "r", encoding="utf-8") as f:
            content_2 = f.read()

        # 文件被覆盖（内容应包含相同的概念数据）
        assert "人工智能" in content_2


def test_generate_report_raises_on_empty_concept_heats():
    """概念热度为空时抛出异常"""
    with tempfile.TemporaryDirectory() as tmpdir:
        generator = MarkdownReportGenerator(output_dir=tmpdir)

        with pytest.raises(ValueError, match="概念热度数据为空"):
            generator.generate([], [], top_n=10)
