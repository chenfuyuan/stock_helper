"""
Data Engineering 市场数据适配器
将 data_engineering 的日线数据转换为 market_insight 领域层 DTO
"""

from datetime import date
from typing import List

from src.modules.data_engineering.container import DataEngineeringContainer
from src.modules.market_insight.domain.dtos.insight_dtos import StockDailyDTO
from src.modules.market_insight.domain.ports.market_data_port import IMarketDataPort


class DeMarketDataAdapter(IMarketDataPort):
    """Data Engineering 市场数据适配器"""

    def __init__(self, de_container: DataEngineeringContainer):
        self._get_daily_bars_by_date_use_case = (
            de_container.get_daily_bars_by_date_use_case()
        )

    async def get_daily_bars_by_date(self, trade_date: date) -> List[StockDailyDTO]:
        """
        获取指定交易日全市场日线数据
        :param trade_date: 交易日期
        :return: 股票日线 DTO 列表
        """
        de_bars = await self._get_daily_bars_by_date_use_case.execute(
            trade_date=trade_date
        )

        return [
            StockDailyDTO(
                third_code=bar.third_code,
                stock_name=bar.stock_name or "",
                trade_date=bar.trade_date,
                close=bar.close,
                pct_chg=bar.pct_chg,
                amount=bar.amount,
            )
            for bar in de_bars
        ]
