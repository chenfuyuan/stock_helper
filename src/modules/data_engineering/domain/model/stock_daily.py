from datetime import date
from typing import Optional

from pydantic import ConfigDict, Field

from src.shared.domain.base_entity import BaseEntity


class StockDaily(BaseEntity):
    """
    股票日线行情领域实体
    Stock Daily Quotation Domain Entity
    """

    third_code: str = Field(
        ..., description="第三方系统代码 (如 Tushare 的 ts_code)"
    )
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

    adj_factor: Optional[float] = Field(None, description="复权因子")
    turnover_rate: Optional[float] = Field(None, description="换手率")
    turnover_rate_f: Optional[float] = Field(
        None, description="换手率(自由流通股)"
    )
    volume_ratio: Optional[float] = Field(None, description="量比")
    pe: Optional[float] = Field(None, description="市盈率")
    pe_ttm: Optional[float] = Field(None, description="市盈率TTM")
    pb: Optional[float] = Field(None, description="市净率")
    ps: Optional[float] = Field(None, description="市销率")
    ps_ttm: Optional[float] = Field(None, description="市销率TTM")
    dv_ratio: Optional[float] = Field(None, description="股息率")
    dv_ttm: Optional[float] = Field(None, description="股息率TTM")
    total_share: Optional[float] = Field(None, description="总股本")
    float_share: Optional[float] = Field(None, description="流通股本")
    free_share: Optional[float] = Field(None, description="自由流通股本")
    total_mv: Optional[float] = Field(None, description="总市值")
    circ_mv: Optional[float] = Field(None, description="流通市值")
    source: str = Field("tushare", description="数据来源")

    model_config = ConfigDict(from_attributes=True)
