from pydantic import BaseModel, Field


class LimitUpPoolDTO(BaseModel):
    """
    涨停池数据 DTO
    用于从外部数据源获取涨停池快照数据
    """

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


class BrokenBoardDTO(BaseModel):
    """
    炸板池数据 DTO
    用于从外部数据源获取炸板池快照数据
    """

    third_code: str = Field(..., description="股票代码（系统标准格式，如 000001.SZ）")
    stock_name: str = Field(..., description="股票名称")
    pct_chg: float = Field(..., description="涨跌幅（百分比）")
    close: float = Field(..., description="最新价")
    amount: float = Field(..., description="成交额")
    turnover_rate: float = Field(..., description="换手率")
    open_count: int = Field(..., description="开板次数")
    first_limit_up_time: str | None = Field(None, description="首次封板时间")
    last_open_time: str | None = Field(None, description="最后开板时间")
    industry: str = Field(..., description="所属行业")


class PreviousLimitUpDTO(BaseModel):
    """
    昨日涨停表现数据 DTO
    用于从外部数据源获取昨日涨停股今日表现数据
    """

    third_code: str = Field(..., description="股票代码（系统标准格式，如 000001.SZ）")
    stock_name: str = Field(..., description="股票名称")
    pct_chg: float = Field(..., description="今日涨跌幅（百分比）")
    close: float = Field(..., description="最新价")
    amount: float = Field(..., description="成交额")
    turnover_rate: float = Field(..., description="换手率")
    yesterday_consecutive_boards: int = Field(..., description="昨日连板天数")
    industry: str = Field(..., description="所属行业")
