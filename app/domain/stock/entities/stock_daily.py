from datetime import date
from pydantic import Field, ConfigDict
from app.domain.base_entity import BaseEntity

class StockDaily(BaseEntity):
    """
    股票日线行情领域实体
    Stock Daily Quotation Domain Entity
    """
    third_code: str = Field(..., description="第三方系统代码 (如 Tushare 的 ts_code)")
    trade_date: date = Field(..., description="交易日期")
    open: float = Field(..., description="开盘价")
    high: float = Field(..., description="最高价")
    low: float = Field(..., description="最低价")
    close: float = Field(..., description="收盘价")
    pre_close: float = Field(..., description="昨收价")
    change: float = Field(..., description="涨跌额")
    pct_chg: float = Field(..., description="涨跌幅")
    vol: float = Field(..., description="成交量")
    amount: float = Field(..., description="成交额")
    source: str = Field("tushare", description="数据来源")

    model_config = ConfigDict(from_attributes=True)
