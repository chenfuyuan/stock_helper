"""
按标的与日期区间返回日线数据的 Application 接口。
供 Research 等模块通过 Application 层获取日线，不直接依赖 repository 或 domain 实现。
"""

from datetime import date
from typing import List

from pydantic import BaseModel, Field

from src.modules.data_engineering.domain.model.stock_daily import StockDaily
from src.modules.data_engineering.domain.ports.repositories.market_quote_repo import (
    IMarketQuoteRepository,
)


class DailyBarDTO(BaseModel):
    """日线 DTO，仅暴露开高低收量、涨跌幅等分析所需字段。"""

    trade_date: date = Field(..., description="交易日期")
    open: float = Field(..., description="开盘价")
    high: float = Field(..., description="最高价")
    low: float = Field(..., description="最低价")
    close: float = Field(..., description="收盘价")
    vol: float = Field(..., description="成交量")
    amount: float = Field(default=0.0, description="成交额")
    pct_chg: float = Field(default=0.0, description="涨跌幅（%）")

    model_config = {"frozen": True}


class GetDailyBarsForTickerUseCase:
    """
    按标的（third_code）与日期区间查询日线，返回 DTO 列表。
    其他模块仅通过本用例获取日线，不直接依赖 repository。
    """

    def __init__(self, market_quote_repo: IMarketQuoteRepository):
        self._repo = market_quote_repo

    async def execute(
        self,
        ticker: str,
        start_date: date,
        end_date: date,
    ) -> List[DailyBarDTO]:
        """
        执行查询。ticker 为第三方代码（如 000001.SZ）。
        返回按 trade_date 升序的日线 DTO 列表。
        """
        dailies: List[StockDaily] = (
            await self._repo.get_by_third_code_and_date_range(
                third_code=ticker,
                start_date=start_date,
                end_date=end_date,
            )
        )
        return [
            DailyBarDTO(
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
