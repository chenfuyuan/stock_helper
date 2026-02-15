"""
GenerateDailyReportCmd 集成测试
验证完整流程：计算 → 持久化 → 报告生成
"""

import tempfile
from datetime import date
from unittest.mock import AsyncMock, Mock

import pytest

from src.modules.market_insight.application.commands.generate_daily_report_cmd import (
    GenerateDailyReportCmd,
)
from src.modules.market_insight.domain.dtos.insight_dtos import (
    ConceptInfoDTO,
    ConceptStockDTO,
    ConceptWithStocksDTO,
    StockDailyDTO,
)
from src.modules.market_insight.domain.services.concept_heat_calculator import (
    ConceptHeatCalculator,
)
from src.modules.market_insight.domain.services.limit_up_scanner import LimitUpScanner
from src.modules.market_insight.infrastructure.report.markdown_report_generator import (
    MarkdownReportGenerator,
)


@pytest.mark.asyncio
async def test_generate_daily_report_full_workflow():
    """完整流程测试：mock DE 数据，验证计算 → 持久化 → 报告生成"""

    # Mock Ports
    concept_data_port = AsyncMock()
    market_data_port = AsyncMock()

    # Mock Repositories
    concept_heat_repo = AsyncMock()
    limit_up_repo = AsyncMock()

    # 准备 mock 数据
    trade_date = date(2025, 1, 6)

    # 概念数据
    concept_data_port.get_all_concepts_with_stocks.return_value = [
        ConceptWithStocksDTO(
            code="BK0001",
            name="人工智能",
            stocks=[
                ConceptStockDTO(third_code="000001.SZ", stock_name="股票A"),
                ConceptStockDTO(third_code="000002.SZ", stock_name="股票B"),
            ],
        ),
    ]

    # 行情数据
    market_data_port.get_daily_bars_by_date.return_value = [
        StockDailyDTO(
            third_code="000001.SZ",
            stock_name="股票A",
            trade_date=trade_date,
            close=12.0,
            pct_chg=10.0,
            amount=200000000.0,
        ),
        StockDailyDTO(
            third_code="000002.SZ",
            stock_name="股票B",
            trade_date=trade_date,
            close=20.0,
            pct_chg=5.0,
            amount=300000000.0,
        ),
    ]

    # 真实的 Domain Services
    concept_heat_calculator = ConceptHeatCalculator()
    limit_up_scanner = LimitUpScanner()

    # 使用临时目录作为报告输出
    with tempfile.TemporaryDirectory() as tmpdir:
        report_generator = MarkdownReportGenerator(output_dir=tmpdir)

        cmd = GenerateDailyReportCmd(
            concept_data_port=concept_data_port,
            market_data_port=market_data_port,
            concept_heat_repo=concept_heat_repo,
            limit_up_repo=limit_up_repo,
            concept_heat_calculator=concept_heat_calculator,
            limit_up_scanner=limit_up_scanner,
            report_generator=report_generator,
        )

        # 执行命令
        result = await cmd.execute(trade_date)

        # 验证结果
        assert result.trade_date == trade_date
        assert result.concept_count == 1
        assert result.limit_up_count == 1
        assert result.report_path.endswith("2025-01-06-market-insight.md")
        assert result.elapsed_seconds > 0

        # 验证 Repositories 被调用
        concept_heat_repo.save_all.assert_called_once()
        limit_up_repo.save_all.assert_called_once()

        # 验证持久化数据
        saved_heats = concept_heat_repo.save_all.call_args[0][0]
        assert len(saved_heats) == 1
        assert saved_heats[0].concept_code == "BK0001"
        assert saved_heats[0].avg_pct_chg == 7.5

        saved_stocks = limit_up_repo.save_all.call_args[0][0]
        assert len(saved_stocks) == 1
        assert saved_stocks[0].third_code == "000001.SZ"


@pytest.mark.asyncio
async def test_generate_daily_report_no_market_data():
    """无行情数据时的处理"""

    concept_data_port = AsyncMock()
    market_data_port = AsyncMock()
    concept_heat_repo = AsyncMock()
    limit_up_repo = AsyncMock()

    trade_date = date(2025, 1, 4)

    # 返回空行情数据（非交易日）
    market_data_port.get_daily_bars_by_date.return_value = []

    concept_heat_calculator = ConceptHeatCalculator()
    limit_up_scanner = LimitUpScanner()

    with tempfile.TemporaryDirectory() as tmpdir:
        report_generator = MarkdownReportGenerator(output_dir=tmpdir)

        cmd = GenerateDailyReportCmd(
            concept_data_port=concept_data_port,
            market_data_port=market_data_port,
            concept_heat_repo=concept_heat_repo,
            limit_up_repo=limit_up_repo,
            concept_heat_calculator=concept_heat_calculator,
            limit_up_scanner=limit_up_scanner,
            report_generator=report_generator,
        )

        result = await cmd.execute(trade_date)

        # 验证结果
        assert result.trade_date == trade_date
        assert result.concept_count == 0
        assert result.limit_up_count == 0
        assert result.report_path == ""

        # 验证 Repositories 未被调用
        concept_heat_repo.save_all.assert_not_called()
        limit_up_repo.save_all.assert_not_called()
