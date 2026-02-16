"""
获取股票基础信息（含最新行情）的 Application 查询接口。

StockBasicInfoDTO 仅暴露基本类型字段，不直接引用 Domain Entity，
符合 tech-standards DTO 规范。
"""

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field

from src.modules.data_engineering.domain.ports.repositories.market_quote_repo import (
    IMarketQuoteRepository,
)
from src.modules.data_engineering.domain.ports.repositories.stock_basic_repo import (
    IStockBasicRepository,
)


class StockBasicInfoDTO(BaseModel):
    """股票基础信息 DTO——展开基本类型字段，不嵌套 Domain Entity。"""

    # 基础信息（来自 StockInfo）
    third_code: str = Field(..., description="第三方系统代码（如 000001.SZ）")
    symbol: str = Field(..., description="股票代码（如 000001）")
    name: str = Field(..., description="股票名称")
    area: Optional[str] = Field(None, description="所在地域")
    industry: Optional[str] = Field(None, description="所属行业")
    market: Optional[str] = Field(None, description="市场类型")
    list_date: Optional[date] = Field(None, description="上市日期")
    list_status: Optional[str] = Field(None, description="上市状态")

    # 最新行情（来自 StockDaily，可能为空）
    latest_trade_date: Optional[date] = Field(None, description="最新交易日期")
    latest_close: Optional[float] = Field(None, description="最新收盘价")
    latest_pct_chg: Optional[float] = Field(None, description="最新涨跌幅（%）")
    latest_vol: Optional[float] = Field(None, description="最新成交量")
    latest_amount: Optional[float] = Field(None, description="最新成交额")

    model_config = {"frozen": True}


class GetStockBasicInfoUseCase:
    """
    获取股票基础信息用例（只读查询，归位至 queries）。

    内部完成 Entity→DTO 映射，对外仅暴露 DTO。
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
        执行获取逻辑。

        Args:
            symbol: 股票代码（如 000001 或 000001.SZ）

        Returns:
            聚合信息 DTO，未找到时返回 None
        """
        if "." in symbol:
            stock_info = await self.stock_repo.get_by_third_code(symbol)
        else:
            stock_info = await self.stock_repo.get_by_symbol(symbol)

        if not stock_info:
            return None

        stock_daily = await self.daily_repo.get_latest_by_third_code(stock_info.third_code)

        return StockBasicInfoDTO(
            third_code=stock_info.third_code,
            symbol=stock_info.symbol,
            name=stock_info.name,
            area=stock_info.area,
            industry=stock_info.industry,
            market=stock_info.market.value if stock_info.market else None,
            list_date=stock_info.list_date,
            list_status=stock_info.list_status.value if stock_info.list_status else None,
            latest_trade_date=stock_daily.trade_date if stock_daily else None,
            latest_close=stock_daily.close if stock_daily else None,
            latest_pct_chg=stock_daily.pct_chg if stock_daily else None,
            latest_vol=stock_daily.vol if stock_daily else None,
            latest_amount=stock_daily.amount if stock_daily else None,
        )
