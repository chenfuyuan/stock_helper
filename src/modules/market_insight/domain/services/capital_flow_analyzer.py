from collections import defaultdict

from src.modules.market_insight.domain.dtos.capital_flow_dtos import (
    DragonTigerAnalysis,
    DragonTigerItemDTO,
    DragonTigerStockSummary,
    SectorCapitalFlowAnalysis,
    SectorCapitalFlowItemDTO,
)


class CapitalFlowAnalyzer:
    """
    资金流向分析器（领域服务）
    纯函数式计算，不依赖外部 I/O
    """

    def analyze_dragon_tiger(self, details: list[DragonTigerItemDTO]) -> DragonTigerAnalysis:
        """
        分析龙虎榜数据
        
        Args:
            details: 龙虎榜详情数据
            
        Returns:
            DragonTigerAnalysis: 龙虎榜分析结果
        """
        if not details:
            return DragonTigerAnalysis(
                total_count=0,
                total_net_buy=0.0,
                top_net_buy_stocks=[],
                top_net_sell_stocks=[],
                institutional_activity=[],
            )

        # 按股票代码聚合
        stock_aggregates: dict[str, dict] = defaultdict(
            lambda: {
                "third_code": "",
                "stock_name": "",
                "pct_chg": 0.0,
                "net_amount": 0.0,
                "reason": "",
                "has_institutional": False,
            }
        )

        total_net_buy = 0.0

        for detail in details:
            key = detail.third_code
            agg = stock_aggregates[key]

            # 首次遇到该股票时填充基础信息
            if not agg["third_code"]:
                agg["third_code"] = detail.third_code
                agg["stock_name"] = detail.stock_name
                agg["pct_chg"] = detail.pct_chg
                agg["reason"] = detail.reason

            # 累加净买入额
            agg["net_amount"] += detail.net_amount
            total_net_buy += detail.net_amount

            # 检查是否有机构参与
            if not agg["has_institutional"]:
                for seat in detail.buy_seats + detail.sell_seats:
                    if "机构" in seat.get("seat_name", ""):
                        agg["has_institutional"] = True
                        break

        # 转换为 DragonTigerStockSummary 列表
        stock_summaries = [
            DragonTigerStockSummary(
                third_code=agg["third_code"],
                stock_name=agg["stock_name"],
                pct_chg=agg["pct_chg"],
                net_amount=agg["net_amount"],
                reason=agg["reason"],
            )
            for agg in stock_aggregates.values()
        ]

        # 按净买入额排序，取前 10
        sorted_by_net_buy = sorted(stock_summaries, key=lambda x: x.net_amount, reverse=True)
        top_net_buy_stocks = sorted_by_net_buy[:10]

        # 按净卖出额排序（负值最大），取前 10
        sorted_by_net_sell = sorted(stock_summaries, key=lambda x: x.net_amount)
        top_net_sell_stocks = sorted_by_net_sell[:10]

        # 机构参与的个股
        institutional_activity = [
            DragonTigerStockSummary(
                third_code=agg["third_code"],
                stock_name=agg["stock_name"],
                pct_chg=agg["pct_chg"],
                net_amount=agg["net_amount"],
                reason=agg["reason"],
            )
            for agg in stock_aggregates.values()
            if agg["has_institutional"]
        ]

        return DragonTigerAnalysis(
            total_count=len(stock_aggregates),
            total_net_buy=total_net_buy,
            top_net_buy_stocks=top_net_buy_stocks,
            top_net_sell_stocks=top_net_sell_stocks,
            institutional_activity=institutional_activity,
        )

    def analyze_sector_capital_flow(
        self, flows: list[SectorCapitalFlowItemDTO]
    ) -> SectorCapitalFlowAnalysis:
        """
        分析板块资金流向
        
        Args:
            flows: 板块资金流向数据
            
        Returns:
            SectorCapitalFlowAnalysis: 板块资金流向分析结果
        """
        if not flows:
            return SectorCapitalFlowAnalysis(
                total_sectors=0,
                top_inflow_sectors=[],
                top_outflow_sectors=[],
                avg_pct_chg=0.0,
            )

        total_sectors = len(flows)

        # 按净流入额降序排列，取前 10
        sorted_by_inflow = sorted(flows, key=lambda x: x.net_amount, reverse=True)
        top_inflow_sectors = sorted_by_inflow[:10]

        # 按净流出额排列（负值最大），取前 10
        sorted_by_outflow = sorted(flows, key=lambda x: x.net_amount)
        top_outflow_sectors = sorted_by_outflow[:10]

        # 计算平均涨跌幅
        avg_pct_chg = sum(flow.pct_chg for flow in flows) / total_sectors

        return SectorCapitalFlowAnalysis(
            total_sectors=total_sectors,
            top_inflow_sectors=top_inflow_sectors,
            top_outflow_sectors=top_outflow_sectors,
            avg_pct_chg=avg_pct_chg,
        )
