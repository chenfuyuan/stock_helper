"""
按标的与日期区间返回估值日线数据的 Application 接口。
供 Research 估值建模师模块获取历史估值指标（PE、PB、PS 等），用于历史分位点计算。
"""
from datetime import date
from typing import List, Optional

from pydantic import BaseModel, Field

from src.modules.data_engineering.domain.model.daily_bar import StockDaily
from src.modules.data_engineering.domain.ports.repositories.market_quote_repo import (
    IMarketQuoteRepository,
)


class ValuationDailyDTO(BaseModel):
    """
    估值日线 DTO，仅暴露估值分析所需字段。
    用于计算 PE/PB/PS 历史分位点等估值模型指标。
    """

    trade_date: date = Field(..., description="交易日期")
    close: float = Field(..., description="收盘价")
    pe_ttm: Optional[float] = Field(None, description="市盈率TTM")
    pb: Optional[float] = Field(None, description="市净率")
    ps_ttm: Optional[float] = Field(None, description="市销率TTM")
    dv_ratio: Optional[float] = Field(None, description="股息率")
    total_mv: Optional[float] = Field(None, description="总市值（万元）")

    model_config = {"frozen": True}


class GetValuationDailiesForTickerUseCase:
    """
    按标的（third_code）与日期区间查询估值日线，返回含估值字段的 DTO 列表。
    其他模块仅通过本用例获取估值日线，不直接依赖 repository。
    """

    def __init__(self, market_quote_repo: IMarketQuoteRepository):
        self._repo = market_quote_repo

    async def execute(
        self,
        ticker: str,
        start_date: date,
        end_date: date,
    ) -> List[ValuationDailyDTO]:
        """
        执行查询。ticker 为第三方代码（如 000001.SZ）。
        返回按 trade_date 升序的估值日线 DTO 列表。
        """
        dailies: List[StockDaily] = await self._repo.get_valuation_dailies(
            third_code=ticker,
            start_date=start_date,
            end_date=end_date,
        )
        return [
            ValuationDailyDTO(
                trade_date=d.trade_date,
                close=d.close,
                pe_ttm=d.pe_ttm,
                pb=d.pb,
                ps_ttm=d.ps_ttm,
                dv_ratio=d.dv_ratio,
                total_mv=d.total_mv,
            )
            for d in dailies
        ]
