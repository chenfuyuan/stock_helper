from datetime import date

from pydantic import Field

from src.shared.domain.base_entity import BaseEntity


class PreviousLimitUpStock(BaseEntity):
    """
    昨日涨停表现领域实体
    表示昨日涨停股今日的表现记录
    """

    trade_date: date = Field(..., description="交易日期（今日日期，即表现观察日）")
    third_code: str = Field(..., description="股票代码（系统标准格式，如 000001.SZ）")
    stock_name: str = Field(..., description="股票名称")
    pct_chg: float = Field(..., description="今日涨跌幅（百分比）")
    close: float = Field(..., description="最新价")
    amount: float = Field(..., description="成交额")
    turnover_rate: float = Field(..., description="换手率")
    yesterday_consecutive_boards: int = Field(..., description="昨日连板天数")
    industry: str = Field(..., description="所属行业")
