"""
获取日线 Port 的 Adapter。
内部调用 data_engineering 的 GetDailyBarsForTickerUseCase（Application 接口），
不直接依赖 data_engineering 的 repository 或 domain。
"""
from datetime import date
from typing import List

from src.modules.data_engineering.application.queries.get_daily_bars_for_ticker import (
    GetDailyBarsForTickerUseCase,
)
from src.modules.research.domain.dtos.daily_bar_input import DailyBarInput
from src.modules.research.domain.ports.market_quote import IMarketQuotePort


class MarketQuoteAdapter(IMarketQuotePort):
    """通过 data_engineering 的 Application 接口获取日线，转为 Research 的 DailyBarInput。"""

    def __init__(self, get_daily_bars_use_case: GetDailyBarsForTickerUseCase):
        self._get_daily_bars = get_daily_bars_use_case

    async def get_daily_bars(
        self, ticker: str, start_date: date, end_date: date
    ) -> List[DailyBarInput]:
        dto_list = await self._get_daily_bars.execute(
            ticker=ticker, start_date=start_date, end_date=end_date
        )
        return [
            DailyBarInput(
                trade_date=d.trade_date,
                open=d.open,
                high=d.high,
                low=d.low,
                close=d.close,
                vol=d.vol,
                amount=d.amount,
                pct_chg=getattr(d, "pct_chg", 0.0) or 0.0,
            )
            for d in dto_list
        ]
