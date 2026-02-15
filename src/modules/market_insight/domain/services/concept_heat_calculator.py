"""
概念板块热度计算领域服务
"""

from typing import Dict, List

from src.modules.market_insight.domain.dtos.insight_dtos import (
    ConceptWithStocksDTO,
    StockDailyDTO,
)
from src.modules.market_insight.domain.model.concept_heat import ConceptHeat


class ConceptHeatCalculator:
    """概念板块热度计算器"""

    def calculate(
        self,
        concepts: List[ConceptWithStocksDTO],
        daily_bars: Dict[str, StockDailyDTO],
    ) -> List[ConceptHeat]:
        """
        计算概念板块热度
        :param concepts: 概念及成分股列表
        :param daily_bars: 以 third_code 为 key 的日线数据字典
        :return: 概念热度列表
        """
        results: List[ConceptHeat] = []

        for concept in concepts:
            # 筛选出有行情数据的成分股
            valid_stocks = [
                s for s in concept.stocks if s.third_code in daily_bars
            ]

            if not valid_stocks:
                # 全部停牌，排除该概念
                continue

            # 收集成分股的涨跌幅和成交额
            pct_chgs: List[float] = []
            total_amount = 0.0
            up_count = 0
            down_count = 0
            limit_up_count = 0

            for stock in valid_stocks:
                bar = daily_bars[stock.third_code]
                pct_chg = bar.pct_chg
                pct_chgs.append(pct_chg)
                total_amount += bar.amount

                if pct_chg > 0:
                    up_count += 1
                elif pct_chg < 0:
                    down_count += 1

                # 涨停判定
                if self._is_limit_up(stock.stock_name, bar.pct_chg, stock.third_code):
                    limit_up_count += 1

            # 等权平均涨跌幅
            avg_pct_chg = sum(pct_chgs) / len(pct_chgs)

            # 从第一个有效股票的行情中获取 trade_date
            first_bar = daily_bars[valid_stocks[0].third_code]
            trade_date = first_bar.trade_date

            heat = ConceptHeat(
                trade_date=trade_date,
                concept_code=concept.code,
                concept_name=concept.name,
                avg_pct_chg=avg_pct_chg,
                stock_count=len(valid_stocks),
                up_count=up_count,
                down_count=down_count,
                limit_up_count=limit_up_count,
                total_amount=total_amount,
            )

            results.append(heat)

        return results

    def _is_limit_up(self, stock_name: str, pct_chg: float, third_code: str) -> bool:
        """
        判断是否涨停
        :param stock_name: 股票名称
        :param pct_chg: 涨跌幅
        :param third_code: 股票代码
        :return: 是否涨停
        """
        # ST 股票判定
        if "ST" in stock_name.upper():
            return pct_chg >= 4.9

        # 北交所（代码以 4 或 8 开头）
        if third_code.startswith("4") or third_code.startswith("8"):
            return pct_chg >= 29.5

        # 科创板（代码以 68 开头）
        if third_code.startswith("68"):
            return pct_chg >= 19.8

        # 创业板（代码以 3 开头）
        if third_code.startswith("3"):
            return pct_chg >= 19.8

        # 主板/中小板（代码以 0 或 6 开头）
        if third_code.startswith("0") or third_code.startswith("6"):
            return pct_chg >= 9.9

        # 默认主板标准
        return pct_chg >= 9.9
