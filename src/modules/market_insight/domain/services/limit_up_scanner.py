"""
涨停扫描领域服务
"""

from typing import Dict, List

from src.modules.market_insight.domain.dtos.insight_dtos import (
    ConceptInfoDTO,
    StockDailyDTO,
)
from src.modules.market_insight.domain.model.enums import LimitType
from src.modules.market_insight.domain.model.limit_up_stock import LimitUpStock, Concept


class LimitUpScanner:
    """涨停扫描器"""

    def scan(
        self,
        daily_bars: List[StockDailyDTO],
        concept_stock_map: Dict[str, List[ConceptInfoDTO]],
    ) -> List[LimitUpStock]:
        """
        扫描涨停股并映射概念归因
        :param daily_bars: 当日全市场日线数据
        :param concept_stock_map: 以 third_code 为 key、该股票所属概念列表为 value 的映射字典
        :return: 涨停股列表
        """
        limit_up_stocks: List[LimitUpStock] = []

        for bar in daily_bars:
            limit_type = self._determine_limit_type(bar.stock_name, bar.third_code, bar.pct_chg)
            
            if limit_type is None:
                continue

            # 获取所属概念
            concept_infos = concept_stock_map.get(bar.third_code, [])
            concepts = [Concept(code=c.code, name=c.name) for c in concept_infos]

            limit_up_stock = LimitUpStock(
                trade_date=bar.trade_date,
                third_code=bar.third_code,
                stock_name=bar.stock_name,
                pct_chg=bar.pct_chg,
                close=bar.close,
                amount=bar.amount,
                concepts=concepts,
                limit_type=limit_type,
            )

            limit_up_stocks.append(limit_up_stock)

        return limit_up_stocks

    def _determine_limit_type(
        self, stock_name: str, third_code: str, pct_chg: float
    ) -> LimitType | None:
        """
        判断涨停类型
        :param stock_name: 股票名称
        :param third_code: 股票代码
        :param pct_chg: 涨跌幅
        :return: 涨停类型，若未涨停则返回 None
        """
        # ST 股票判定
        if "ST" in stock_name.upper():
            if pct_chg >= 4.9:
                return LimitType.ST
            return None

        # 北交所（代码以 4 或 8 开头）
        if third_code.startswith("4") or third_code.startswith("8"):
            if pct_chg >= 29.5:
                return LimitType.BSE
            return None

        # 科创板（代码以 68 开头）
        if third_code.startswith("68"):
            if pct_chg >= 19.8:
                return LimitType.STAR
            return None

        # 创业板（代码以 3 开头）
        if third_code.startswith("3"):
            if pct_chg >= 19.8:
                return LimitType.GEM
            return None

        # 主板/中小板（代码以 0 或 6 开头）
        if third_code.startswith("0") or third_code.startswith("6"):
            if pct_chg >= 9.9:
                return LimitType.MAIN_BOARD
            return None

        # 默认主板标准
        if pct_chg >= 9.9:
            return LimitType.MAIN_BOARD

        return None
