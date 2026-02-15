from datetime import date

from pydantic import Field

from src.shared.domain.base_entity import BaseEntity


class LimitUpPoolStock(BaseEntity):
    """
    涨停池股票领域实体
    表示某交易日的涨停池快照记录（含连板天数）
    """

    trade_date: date = Field(..., description="交易日期")
    third_code: str = Field(..., description="股票代码（系统标准格式，如 000001.SZ）")
    stock_name: str = Field(..., description="股票名称")
    pct_chg: float = Field(..., description="涨跌幅（百分比）")
    close: float = Field(..., description="最新价")
    amount: float = Field(..., description="成交额")
    turnover_rate: float = Field(..., description="换手率")
    consecutive_boards: int = Field(..., description="连板天数（首板为 1）")
    first_limit_up_time: str | None = Field(None, description="首次封板时间")
    last_limit_up_time: str | None = Field(None, description="最后封板时间")
    industry: str = Field(..., description="所属行业")
