"""
单元测试：CapitalFlowAnalyzer 领域服务
Test-First：先定义测试用例，再实现领域服务
"""

import pytest

from src.modules.market_insight.domain.dtos.capital_flow_dtos import (
    DragonTigerItemDTO,
    SectorCapitalFlowItemDTO,
)
from src.modules.market_insight.domain.services.capital_flow_analyzer import (
    CapitalFlowAnalyzer,
)


class TestCapitalFlowAnalyzer:
    """测试资金流向分析器"""

    @pytest.fixture
    def analyzer(self):
        """创建分析器实例"""
        return CapitalFlowAnalyzer()

    def test_analyze_dragon_tiger_normal(self, analyzer):
        """测试龙虎榜分析 - 正常情况"""
        details = [
            DragonTigerItemDTO(
                third_code="000001.SZ",
                stock_name="平安银行",
                pct_chg=10.0,
                close=15.5,
                reason="日涨幅偏离值达7%",
                net_amount=5000000.0,
                buy_amount=8000000.0,
                sell_amount=3000000.0,
                buy_seats=[{"seat_name": "机构专用", "buy_amount": 3000000.0}],
                sell_seats=[{"seat_name": "游资席位", "sell_amount": 1500000.0}],
            ),
            DragonTigerItemDTO(
                third_code="000002.SZ",
                stock_name="万科A",
                pct_chg=8.5,
                close=10.2,
                reason="连续三个交易日涨幅偏离值累计达20%",
                net_amount=-3000000.0,
                buy_amount=4000000.0,
                sell_amount=7000000.0,
                buy_seats=[{"seat_name": "游资席位", "buy_amount": 2000000.0}],
                sell_seats=[{"seat_name": "机构专用", "sell_amount": 3500000.0}],
            ),
            DragonTigerItemDTO(
                third_code="000001.SZ",
                stock_name="平安银行",
                pct_chg=10.0,
                close=15.5,
                reason="日涨幅偏离值达7%",
                net_amount=2000000.0,
                buy_amount=5000000.0,
                sell_amount=3000000.0,
                buy_seats=[],
                sell_seats=[],
            ),
        ]

        result = analyzer.analyze_dragon_tiger(details)

        # 去重后应该有 2 只个股（000001.SZ 出现两次但只算一次）
        assert result.total_count == 2
        
        # 总净买入额应该是所有记录的净额之和
        assert result.total_net_buy == 4000000.0  # 5000000 + (-3000000) + 2000000

        # 验证 top_net_buy_stocks
        assert len(result.top_net_buy_stocks) > 0
        assert result.top_net_buy_stocks[0].stock_name == "平安银行"
        assert result.top_net_buy_stocks[0].net_amount == 7000000.0  # 两条记录合计

        # 验证 top_net_sell_stocks
        assert len(result.top_net_sell_stocks) > 0
        assert result.top_net_sell_stocks[0].stock_name == "万科A"

    def test_analyze_dragon_tiger_institutional_activity(self, analyzer):
        """测试龙虎榜分析 - 机构席位识别"""
        details = [
            DragonTigerItemDTO(
                third_code="000001.SZ",
                stock_name="平安银行",
                pct_chg=10.0,
                close=15.5,
                reason="日涨幅偏离值达7%",
                net_amount=5000000.0,
                buy_amount=8000000.0,
                sell_amount=3000000.0,
                buy_seats=[{"seat_name": "机构专用", "buy_amount": 3000000.0}],
                sell_seats=[],
            ),
            DragonTigerItemDTO(
                third_code="000002.SZ",
                stock_name="万科A",
                pct_chg=8.5,
                close=10.2,
                reason="连续三个交易日涨幅偏离值累计达20%",
                net_amount=-3000000.0,
                buy_amount=4000000.0,
                sell_amount=7000000.0,
                buy_seats=[],
                sell_seats=[{"seat_name": "机构专用", "sell_amount": 3500000.0}],
            ),
            DragonTigerItemDTO(
                third_code="000003.SZ",
                stock_name="万科B",
                pct_chg=5.0,
                close=12.5,
                reason="振幅值达15%",
                net_amount=1000000.0,
                buy_amount=2000000.0,
                sell_amount=1000000.0,
                buy_seats=[{"seat_name": "游资席位", "buy_amount": 1500000.0}],
                sell_seats=[],
            ),
        ]

        result = analyzer.analyze_dragon_tiger(details)

        # 应该有 2 只个股有机构参与
        assert len(result.institutional_activity) == 2
        
        # 验证机构参与的个股
        institutional_codes = {stock.third_code for stock in result.institutional_activity}
        assert "000001.SZ" in institutional_codes
        assert "000002.SZ" in institutional_codes
        assert "000003.SZ" not in institutional_codes

    def test_analyze_dragon_tiger_empty(self, analyzer):
        """测试龙虎榜分析 - 数据为空"""
        result = analyzer.analyze_dragon_tiger([])

        assert result.total_count == 0
        assert result.total_net_buy == 0.0
        assert len(result.top_net_buy_stocks) == 0
        assert len(result.top_net_sell_stocks) == 0
        assert len(result.institutional_activity) == 0

    def test_analyze_sector_capital_flow_normal(self, analyzer):
        """测试板块资金流向分析 - 正常情况"""
        flows = [
            SectorCapitalFlowItemDTO(
                sector_name="人工智能",
                sector_type="概念资金流",
                net_amount=50000000.0,
                inflow_amount=100000000.0,
                outflow_amount=50000000.0,
                pct_chg=3.5,
            ),
            SectorCapitalFlowItemDTO(
                sector_name="低空经济",
                sector_type="概念资金流",
                net_amount=-20000000.0,
                inflow_amount=30000000.0,
                outflow_amount=50000000.0,
                pct_chg=-1.2,
            ),
            SectorCapitalFlowItemDTO(
                sector_name="新能源",
                sector_type="概念资金流",
                net_amount=30000000.0,
                inflow_amount=80000000.0,
                outflow_amount=50000000.0,
                pct_chg=2.8,
            ),
        ]

        result = analyzer.analyze_sector_capital_flow(flows)

        assert result.total_sectors == 3
        
        # 验证净流入排名
        assert len(result.top_inflow_sectors) > 0
        assert result.top_inflow_sectors[0].sector_name == "人工智能"
        assert result.top_inflow_sectors[0].net_amount == 50000000.0

        # 验证净流出排名
        assert len(result.top_outflow_sectors) > 0
        assert result.top_outflow_sectors[0].sector_name == "低空经济"
        assert result.top_outflow_sectors[0].net_amount == -20000000.0

        # 验证平均涨跌幅
        expected_avg = (3.5 - 1.2 + 2.8) / 3
        assert abs(result.avg_pct_chg - expected_avg) < 0.01

    def test_analyze_sector_capital_flow_empty(self, analyzer):
        """测试板块资金流向分析 - 数据为空"""
        result = analyzer.analyze_sector_capital_flow([])

        assert result.total_sectors == 0
        assert len(result.top_inflow_sectors) == 0
        assert len(result.top_outflow_sectors) == 0
        assert result.avg_pct_chg == 0.0

    def test_analyze_sector_capital_flow_top_10(self, analyzer):
        """测试板块资金流向分析 - 验证 Top 10 限制"""
        # 创建 15 个板块数据
        flows = [
            SectorCapitalFlowItemDTO(
                sector_name=f"板块{i}",
                sector_type="概念资金流",
                net_amount=float(i * 1000000),
                inflow_amount=float(i * 2000000),
                outflow_amount=float(i * 1000000),
                pct_chg=float(i),
            )
            for i in range(15)
        ]

        result = analyzer.analyze_sector_capital_flow(flows)

        assert result.total_sectors == 15
        
        # 最多返回 10 个
        assert len(result.top_inflow_sectors) <= 10
        assert len(result.top_outflow_sectors) <= 10
