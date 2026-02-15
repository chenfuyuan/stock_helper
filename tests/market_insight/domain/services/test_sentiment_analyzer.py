"""
单元测试：SentimentAnalyzer 领域服务
Test-First：先定义测试用例，再实现领域服务
"""

import pytest

from src.modules.market_insight.domain.dtos.sentiment_dtos import (
    BrokenBoardItemDTO,
    LimitUpPoolItemDTO,
    PreviousLimitUpItemDTO,
)
from src.modules.market_insight.domain.services.sentiment_analyzer import SentimentAnalyzer


class TestSentimentAnalyzer:
    """测试市场情绪分析器"""

    @pytest.fixture
    def analyzer(self):
        """创建分析器实例"""
        return SentimentAnalyzer()

    def test_analyze_consecutive_board_ladder_normal(self, analyzer):
        """测试连板梯队分布计算 - 正常情况"""
        limit_up_pool = [
            LimitUpPoolItemDTO(
                third_code="000001.SZ",
                stock_name="平安银行",
                pct_chg=10.0,
                close=15.5,
                amount=100000.0,
                consecutive_boards=1,
                industry="银行",
            ),
            LimitUpPoolItemDTO(
                third_code="000002.SZ",
                stock_name="万科A",
                pct_chg=10.0,
                close=10.2,
                amount=50000.0,
                consecutive_boards=1,
                industry="房地产",
            ),
            LimitUpPoolItemDTO(
                third_code="000003.SZ",
                stock_name="万科B",
                pct_chg=10.0,
                close=12.5,
                amount=120000.0,
                consecutive_boards=1,
                industry="房地产",
            ),
            LimitUpPoolItemDTO(
                third_code="601398.SH",
                stock_name="工商银行",
                pct_chg=10.0,
                close=6.2,
                amount=200000.0,
                consecutive_boards=2,
                industry="银行",
            ),
            LimitUpPoolItemDTO(
                third_code="601888.SH",
                stock_name="中国平安",
                pct_chg=10.0,
                close=50.8,
                amount=300000.0,
                consecutive_boards=2,
                industry="保险",
            ),
            LimitUpPoolItemDTO(
                third_code="300001.SZ",
                stock_name="特锐德",
                pct_chg=10.0,
                close=20.5,
                amount=80000.0,
                consecutive_boards=5,
                industry="电气设备",
            ),
        ]

        result = analyzer.analyze_consecutive_board_ladder(limit_up_pool)

        assert result.total_limit_up_count == 6
        assert result.max_height == 5
        assert len(result.tiers) == 3

        # 验证梯队按连板数降序排列
        assert result.tiers[0].board_count == 5
        assert len(result.tiers[0].stocks) == 1
        assert "特锐德" in result.tiers[0].stocks

        assert result.tiers[1].board_count == 2
        assert len(result.tiers[1].stocks) == 2
        assert "工商银行" in result.tiers[1].stocks
        assert "中国平安" in result.tiers[1].stocks

        assert result.tiers[2].board_count == 1
        assert len(result.tiers[2].stocks) == 3

    def test_analyze_consecutive_board_ladder_empty(self, analyzer):
        """测试连板梯队分布计算 - 涨停池为空"""
        result = analyzer.analyze_consecutive_board_ladder([])

        assert result.total_limit_up_count == 0
        assert result.max_height == 0
        assert len(result.tiers) == 0

    def test_analyze_previous_limit_up_performance_normal(self, analyzer):
        """测试昨日涨停今日表现 - 正常情况"""
        previous_limit_up = [
            PreviousLimitUpItemDTO(
                third_code="000001.SZ",
                stock_name="平安银行",
                pct_chg=5.5,
                close=15.5,
                amount=100000.0,
                yesterday_consecutive_boards=1,
                industry="银行",
            ),
            PreviousLimitUpItemDTO(
                third_code="000002.SZ",
                stock_name="万科A",
                pct_chg=3.2,
                close=10.2,
                amount=50000.0,
                yesterday_consecutive_boards=1,
                industry="房地产",
            ),
            PreviousLimitUpItemDTO(
                third_code="000003.SZ",
                stock_name="万科B",
                pct_chg=-2.5,
                close=12.5,
                amount=120000.0,
                yesterday_consecutive_boards=1,
                industry="房地产",
            ),
            PreviousLimitUpItemDTO(
                third_code="601398.SH",
                stock_name="工商银行",
                pct_chg=-5.0,
                close=6.2,
                amount=200000.0,
                yesterday_consecutive_boards=2,
                industry="银行",
            ),
            PreviousLimitUpItemDTO(
                third_code="601888.SH",
                stock_name="中国平安",
                pct_chg=8.0,
                close=50.8,
                amount=300000.0,
                yesterday_consecutive_boards=2,
                industry="保险",
            ),
        ]

        result = analyzer.analyze_previous_limit_up_performance(previous_limit_up)

        assert result.total_count == 5
        assert result.up_count == 3
        assert result.down_count == 2
        assert abs(result.avg_pct_chg - 1.84) < 0.01  # (5.5+3.2-2.5-5.0+8.0)/5
        assert abs(result.profit_rate - 60.0) < 0.01  # 3/5*100

        # 验证 strongest 和 weakest
        assert len(result.strongest) <= 5
        assert result.strongest[0].stock_name == "中国平安"
        assert result.strongest[0].pct_chg == 8.0

        assert len(result.weakest) <= 5
        assert result.weakest[0].stock_name == "工商银行"
        assert result.weakest[0].pct_chg == -5.0

    def test_analyze_previous_limit_up_performance_empty(self, analyzer):
        """测试昨日涨停今日表现 - 数据为空"""
        result = analyzer.analyze_previous_limit_up_performance([])

        assert result.total_count == 0
        assert result.up_count == 0
        assert result.down_count == 0
        assert result.avg_pct_chg == 0.0
        assert result.profit_rate == 0.0
        assert len(result.strongest) == 0
        assert len(result.weakest) == 0

    def test_analyze_previous_limit_up_performance_all_up(self, analyzer):
        """测试昨日涨停今日表现 - 全部上涨"""
        previous_limit_up = [
            PreviousLimitUpItemDTO(
                third_code="000001.SZ",
                stock_name="平安银行",
                pct_chg=5.5,
                close=15.5,
                amount=100000.0,
                yesterday_consecutive_boards=1,
                industry="银行",
            ),
            PreviousLimitUpItemDTO(
                third_code="000002.SZ",
                stock_name="万科A",
                pct_chg=3.2,
                close=10.2,
                amount=50000.0,
                yesterday_consecutive_boards=1,
                industry="房地产",
            ),
        ]

        result = analyzer.analyze_previous_limit_up_performance(previous_limit_up)

        assert result.total_count == 2
        assert result.up_count == 2
        assert result.down_count == 0
        assert result.profit_rate == 100.0

    def test_analyze_broken_board_normal(self, analyzer):
        """测试炸板分析 - 正常情况"""
        limit_up_pool = [
            LimitUpPoolItemDTO(
                third_code="000001.SZ",
                stock_name="平安银行",
                pct_chg=10.0,
                close=15.5,
                amount=100000.0,
                consecutive_boards=1,
                industry="银行",
            ),
            LimitUpPoolItemDTO(
                third_code="000002.SZ",
                stock_name="万科A",
                pct_chg=10.0,
                close=10.2,
                amount=50000.0,
                consecutive_boards=1,
                industry="房地产",
            ),
        ]

        broken_board_pool = [
            BrokenBoardItemDTO(
                third_code="000003.SZ",
                stock_name="万科B",
                pct_chg=8.5,
                close=12.5,
                amount=120000.0,
                open_count=2,
                industry="房地产",
            ),
            BrokenBoardItemDTO(
                third_code="601398.SH",
                stock_name="工商银行",
                pct_chg=7.0,
                close=6.2,
                amount=200000.0,
                open_count=1,
                industry="银行",
            ),
        ]

        result = analyzer.analyze_broken_board(limit_up_pool, broken_board_pool)

        assert result.broken_count == 2
        assert result.total_attempted == 4  # 2 涨停 + 2 炸板
        assert abs(result.broken_rate - 50.0) < 0.01  # 2/4*100
        assert len(result.broken_stocks) == 2

    def test_analyze_broken_board_no_broken(self, analyzer):
        """测试炸板分析 - 无炸板"""
        limit_up_pool = [
            LimitUpPoolItemDTO(
                third_code="000001.SZ",
                stock_name="平安银行",
                pct_chg=10.0,
                close=15.5,
                amount=100000.0,
                consecutive_boards=1,
                industry="银行",
            ),
        ]

        result = analyzer.analyze_broken_board(limit_up_pool, [])

        assert result.broken_count == 0
        assert result.total_attempted == 1
        assert result.broken_rate == 0.0
        assert len(result.broken_stocks) == 0

    def test_analyze_broken_board_all_broken(self, analyzer):
        """测试炸板分析 - 全部炸板"""
        broken_board_pool = [
            BrokenBoardItemDTO(
                third_code="000003.SZ",
                stock_name="万科B",
                pct_chg=8.5,
                close=12.5,
                amount=120000.0,
                open_count=2,
                industry="房地产",
            ),
        ]

        result = analyzer.analyze_broken_board([], broken_board_pool)

        assert result.broken_count == 1
        assert result.total_attempted == 1
        assert result.broken_rate == 100.0

    def test_analyze_broken_board_empty(self, analyzer):
        """测试炸板分析 - 数据为空"""
        result = analyzer.analyze_broken_board([], [])

        assert result.broken_count == 0
        assert result.total_attempted == 0
        assert result.broken_rate == 0.0
        assert len(result.broken_stocks) == 0
