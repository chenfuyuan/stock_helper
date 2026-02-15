"""
单元测试：GenerateDailyReportCmd 扩展功能
Test-First：验证新增的市场情绪和资金流向分析功能
"""

from unittest.mock import AsyncMock, MagicMock
from datetime import date

import pytest

from src.modules.market_insight.application.commands.generate_daily_report_cmd import (
    GenerateDailyReportCmd,
)
from src.modules.market_insight.application.dtos.capital_flow_analysis_dtos import (
    CapitalFlowAnalysisDTO,
)
from src.modules.market_insight.application.dtos.sentiment_metrics_dtos import (
    SentimentMetricsDTO,
)
from src.modules.market_insight.domain.dtos.capital_flow_dtos import (
    DragonTigerAnalysis,
    SectorCapitalFlowAnalysis,
)
from src.modules.market_insight.domain.dtos.sentiment_dtos import (
    BrokenBoardAnalysis,
    ConsecutiveBoardLadder,
    PreviousLimitUpPerformance,
)


class TestGenerateDailyReportCmdExtended:
    """测试 GenerateDailyReportCmd 扩展功能"""

    @pytest.fixture
    def mock_concept_data_port(self):
        """Mock 概念数据端口"""
        port = MagicMock()
        port.get_all_concepts_with_stocks = AsyncMock(return_value=[])
        return port

    @pytest.fixture
    def mock_market_data_port(self):
        """Mock 市场数据端口"""
        port = MagicMock()
        port.get_daily_bars_by_date = AsyncMock(return_value=[])
        return port

    @pytest.fixture
    def mock_sentiment_data_port(self):
        """Mock 市场情绪数据端口"""
        port = MagicMock()
        port.get_limit_up_pool = AsyncMock(return_value=[])
        port.get_broken_board_pool = AsyncMock(return_value=[])
        port.get_previous_limit_up = AsyncMock(return_value=[])
        return port

    @pytest.fixture
    def mock_capital_flow_data_port(self):
        """Mock 资金流向数据端口"""
        port = MagicMock()
        port.get_dragon_tiger = AsyncMock(return_value=[])
        port.get_sector_capital_flow = AsyncMock(return_value=[])
        return port

    @pytest.fixture
    def mock_concept_heat_repo(self):
        """Mock 概念热度仓储"""
        repo = MagicMock()
        repo.save_all = AsyncMock(return_value=None)
        return repo

    @pytest.fixture
    def mock_limit_up_repo(self):
        """Mock 涨停股仓储"""
        repo = MagicMock()
        repo.save_all = AsyncMock(return_value=None)
        return repo

    @pytest.fixture
    def mock_concept_heat_calculator(self):
        """Mock 概念热度计算器"""
        return MagicMock()

    @pytest.fixture
    def mock_limit_up_scanner(self):
        """Mock 涨停股扫描器"""
        return MagicMock()

    @pytest.fixture
    def mock_sentiment_analyzer(self):
        """Mock 市场情绪分析器"""
        analyzer = MagicMock()
        analyzer.analyze_consecutive_board_ladder.return_value = ConsecutiveBoardLadder(
            max_height=0, tiers=[], total_limit_up_count=0
        )
        analyzer.analyze_previous_limit_up_performance.return_value = PreviousLimitUpPerformance(
            total_count=0, up_count=0, down_count=0, avg_pct_chg=0.0, profit_rate=0.0, strongest=[], weakest=[]
        )
        analyzer.analyze_broken_board.return_value = BrokenBoardAnalysis(
            broken_count=0, total_attempted=0, broken_rate=0.0, broken_stocks=[]
        )
        return analyzer

    @pytest.fixture
    def mock_capital_flow_analyzer(self):
        """Mock 资金流向分析器"""
        analyzer = MagicMock()
        analyzer.analyze_dragon_tiger.return_value = DragonTigerAnalysis(
            total_count=0, total_net_buy=0.0, top_net_buy_stocks=[], top_net_sell_stocks=[], institutional_activity=[]
        )
        analyzer.analyze_sector_capital_flow.return_value = SectorCapitalFlowAnalysis(
            total_sectors=0, top_inflow_sectors=[], top_outflow_sectors=[], avg_pct_chg=0.0
        )
        return analyzer

    @pytest.fixture
    def mock_report_generator(self):
        """Mock 报告生成器"""
        generator = MagicMock()
        generator.generate_extended_report = MagicMock(return_value="/path/to/extended_report.md")
        return generator

    @pytest.fixture
    def command(
        self,
        mock_concept_data_port,
        mock_market_data_port,
        mock_sentiment_data_port,
        mock_capital_flow_data_port,
        mock_concept_heat_repo,
        mock_limit_up_repo,
        mock_concept_heat_calculator,
        mock_limit_up_scanner,
        mock_sentiment_analyzer,
        mock_capital_flow_analyzer,
        mock_report_generator,
    ):
        """创建扩展命令实例"""
        return GenerateDailyReportCmd(
            concept_data_port=mock_concept_data_port,
            market_data_port=mock_market_data_port,
            sentiment_data_port=mock_sentiment_data_port,
            capital_flow_data_port=mock_capital_flow_data_port,
            concept_heat_repo=mock_concept_heat_repo,
            limit_up_repo=mock_limit_up_repo,
            concept_heat_calculator=mock_concept_heat_calculator,
            limit_up_scanner=mock_limit_up_scanner,
            sentiment_analyzer=mock_sentiment_analyzer,
            capital_flow_analyzer=mock_capital_flow_analyzer,
            report_generator=mock_report_generator,
        )

    @pytest.mark.asyncio
    async def test_execute_with_sentiment_and_capital_flow_success(self, command):
        """测试完整流程 - 包含情绪和资金分析"""
        test_date = date(2024, 2, 15)

        # Mock 基础数据
        command._market_data_port.get_daily_bars_by_date.return_value = [
            MagicMock(third_code="000001.SZ", pct_chg=10.0)
        ]
        command._concept_data_port.get_all_concepts_with_stocks.return_value = []

        # Mock 情绪数据
        command._sentiment_data_port.get_limit_up_pool.return_value = [
            MagicMock(third_code="000001.SZ", stock_name="平安银行", pct_chg=10.0, consecutive_boards=1)
        ]
        command._sentiment_data_port.get_broken_board_pool.return_value = []
        command._sentiment_data_port.get_previous_limit_up.return_value = []

        # Mock 资金数据
        command._capital_flow_data_port.get_dragon_tiger.return_value = []
        command._capital_flow_data_port.get_sector_capital_flow.return_value = []

        # Mock 分析结果
        sentiment_metrics = SentimentMetricsDTO(
            trade_date=test_date,
            consecutive_board_ladder=ConsecutiveBoardLadder(max_height=1, tiers=[], total_limit_up_count=1),
            previous_limit_up_performance=PreviousLimitUpPerformance(
                total_count=0, up_count=0, down_count=0, avg_pct_chg=0.0, profit_rate=0.0, strongest=[], weakest=[]
            ),
            broken_board_analysis=BrokenBoardAnalysis(broken_count=0, total_attempted=1, broken_rate=0.0, broken_stocks=[]),
        )
        capital_flow_analysis = CapitalFlowAnalysisDTO(
            trade_date=test_date,
            dragon_tiger_analysis=DragonTigerAnalysis(
                total_count=0, total_net_buy=0.0, top_net_buy_stocks=[], top_net_sell_stocks=[], institutional_activity=[]
            ),
            sector_capital_flow_analysis=SectorCapitalFlowAnalysis(
                total_sectors=0, top_inflow_sectors=[], top_outflow_sectors=[], avg_pct_chg=0.0
            ),
        )

        # Mock 报告生成
        command._report_generator.generate_extended_report.return_value = "/path/to/extended_report.md"

        result = await command.execute(test_date)

        # 验证结果包含新字段
        assert result.trade_date == test_date
        assert result.sentiment_metrics is not None
        assert result.capital_flow_analysis is not None
        assert result.report_path == "/path/to/extended_report.md"

        # 验证调用了新的数据端口
        command._sentiment_data_port.get_limit_up_pool.assert_called_once_with(test_date)
        command._sentiment_data_port.get_broken_board_pool.assert_called_once_with(test_date)
        command._sentiment_data_port.get_previous_limit_up.assert_called_once_with(test_date)
        command._capital_flow_data_port.get_dragon_tiger.assert_called_once_with(test_date)
        command._capital_flow_data_port.get_sector_capital_flow.assert_called_once_with(test_date)

        # 验证调用了分析器
        command._sentiment_analyzer.analyze_consecutive_board_ladder.assert_called_once()
        command._sentiment_analyzer.analyze_previous_limit_up_performance.assert_called_once()
        command._sentiment_analyzer.analyze_broken_board.assert_called_once()
        command._capital_flow_analyzer.analyze_dragon_tiger.assert_called_once()
        command._capital_flow_analyzer.analyze_sector_capital_flow.assert_called_once()

        # 验证调用了扩展报告生成
        command._report_generator.generate_extended_report.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_with_sentiment_data_failure(self, command):
        """测试情绪数据失败 - 不中断其他流程"""
        test_date = date(2024, 2, 15)

        # Mock 基础数据
        command._market_data_port.get_daily_bars_by_date.return_value = [
            MagicMock(third_code="000001.SZ", pct_chg=10.0)
        ]
        command._concept_data_port.get_all_concepts_with_stocks.return_value = []

        # Mock 情绪数据失败
        command._sentiment_data_port.get_limit_up_pool.side_effect = Exception("情绪数据获取失败")

        # Mock 资金数据成功
        command._capital_flow_data_port.get_dragon_tiger.return_value = []
        command._capital_flow_data_port.get_sector_capital_flow.return_value = []

        # Mock 报告生成
        command._report_generator.generate_extended_report.return_value = "/path/to/extended_report.md"

        result = await command.execute(test_date)

        # 验证情绪数据为 None，但其他数据正常
        assert result.sentiment_metrics is None
        assert result.capital_flow_analysis is not None
        assert result.report_path == "/path/to/extended_report.md"

        # 验证资金数据仍然被调用
        command._capital_flow_data_port.get_dragon_tiger.assert_called_once_with(test_date)
        command._capital_flow_data_port.get_sector_capital_flow.assert_called_once_with(test_date)

    @pytest.mark.asyncio
    async def test_execute_with_capital_flow_data_failure(self, command):
        """测试资金数据失败 - 不中断其他流程"""
        test_date = date(2024, 2, 15)

        # Mock 基础数据
        command._market_data_port.get_daily_bars_by_date.return_value = [
            MagicMock(third_code="000001.SZ", pct_chg=10.0)
        ]
        command._concept_data_port.get_all_concepts_with_stocks.return_value = []

        # Mock 情绪数据成功
        command._sentiment_data_port.get_limit_up_pool.return_value = []
        command._sentiment_data_port.get_broken_board_pool.return_value = []
        command._sentiment_data_port.get_previous_limit_up.return_value = []

        # Mock 资金数据失败
        command._capital_flow_data_port.get_dragon_tiger.side_effect = Exception("资金数据获取失败")

        # Mock 报告生成
        command._report_generator.generate_extended_report.return_value = "/path/to/extended_report.md"

        result = await command.execute(test_date)

        # 验证资金数据为 None，但情绪数据正常
        assert result.sentiment_metrics is not None
        assert result.capital_flow_analysis is None
        assert result.report_path == "/path/to/extended_report.md"

        # 验证情绪数据仍然被调用
        command._sentiment_data_port.get_limit_up_pool.assert_called_once_with(test_date)
        command._sentiment_data_port.get_broken_board_pool.assert_called_once_with(test_date)
        command._sentiment_data_port.get_previous_limit_up.assert_called_once_with(test_date)

    @pytest.mark.asyncio
    async def test_execute_with_no_market_data(self, command):
        """测试无市场数据 - 返回空结果"""
        test_date = date(2024, 2, 15)

        # Mock 无市场数据
        command._market_data_port.get_daily_bars_by_date.return_value = []

        result = await command.execute(test_date)

        # 验证返回空结果
        assert result.concept_count == 0
        assert result.limit_up_count == 0
        assert result.sentiment_metrics is None
        assert result.capital_flow_analysis is None
        assert result.report_path == ""
