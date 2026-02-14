from typing import Optional

from pydantic import BaseModel

from src.modules.data_engineering.domain.model.stock import StockInfo
from src.modules.data_engineering.domain.model.stock_daily import StockDaily
from src.modules.data_engineering.domain.ports.repositories.market_quote_repo import (
    IMarketQuoteRepository,
)
from src.modules.data_engineering.domain.ports.repositories.stock_basic_repo import (
    IStockBasicRepository,
)


class StockBasicInfoDTO(BaseModel):
    info: StockInfo
    daily: Optional[StockDaily] = None


class GetStockBasicInfoUseCase:
    """
    获取股票基础信息用例（只读查询，归位至 queries）。
    """

    def __init__(
        self,
        stock_repo: IStockBasicRepository,
        daily_repo: IMarketQuoteRepository,
    ):
        self.stock_repo = stock_repo
        self.daily_repo = daily_repo

    async def execute(self, symbol: str) -> Optional[StockBasicInfoDTO]:
        """
        执行获取逻辑
        :param symbol: 股票代码 (如 000001)
        :return: 聚合信息 DTO
        """
        if "." in symbol:
            stock_info = await self.stock_repo.get_by_third_code(symbol)
        else:
            stock_info = await self.stock_repo.get_by_symbol(symbol)

        if not stock_info:
            return None

        stock_daily = await self.daily_repo.get_latest_by_third_code(
            stock_info.third_code
        )
        return StockBasicInfoDTO(info=stock_info, daily=stock_daily)
