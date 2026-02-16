"""
按交易日期返回全市场日线数据的 Application 接口。
供 market_insight 等模块通过 Application 层获取全市场某日日线。
"""

from datetime import date
from typing import List

from src.modules.data_engineering.application.dtos.daily_bar_dto import DailyBarDTO
from src.modules.data_engineering.domain.model.stock_daily import StockDaily
from src.modules.data_engineering.domain.ports.repositories.market_quote_repo import (
    IMarketQuoteRepository,
)


class GetDailyBarsByDateUseCase:
    """
    按交易日期查询全市场日线，返回 DTO 列表。
    其他模块仅通过本用例获取全市场某日日线，不直接依赖 repository。
    """

    def __init__(self, market_quote_repo: IMarketQuoteRepository):
        self._repo = market_quote_repo

    async def execute(
        self,
        trade_date: date,
    ) -> List[DailyBarDTO]:
        """
        执行查询。trade_date 为交易日期。
        返回该日期所有股票的日线 DTO 列表。
        """
        dailies: List[StockDaily] = await self._repo.get_all_by_trade_date(
            trade_date=trade_date
        )
        return [
            DailyBarDTO(
                third_code=d.third_code,
                stock_name=d.stock_name,
                trade_date=d.trade_date,
                open=d.open,
                high=d.high,
                low=d.low,
                close=d.close,
                vol=d.vol,
                amount=d.amount,
                pct_chg=getattr(d, "pct_chg", 0.0) or 0.0,
            )
            for d in dailies
        ]
