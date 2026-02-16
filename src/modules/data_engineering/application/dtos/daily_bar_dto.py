"""
日线数据 DTO——统一定义，供多个 Query 复用。

将原先分散在 get_daily_bars_by_date.py 和 get_daily_bars_for_ticker.py 中的
重复 DailyBarDTO 合并为单一版本，包含 third_code 和 stock_name 字段以满足
全市场查询和单标的查询两种场景。
"""

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class DailyBarDTO(BaseModel):
    """日线 DTO，仅暴露开高低收量、涨跌幅等分析所需字段。"""

    third_code: str = Field(..., description="股票代码")
    stock_name: str = Field(default="", description="股票名称")
    trade_date: date = Field(..., description="交易日期")
    open: float = Field(..., description="开盘价")
    high: float = Field(..., description="最高价")
    low: float = Field(..., description="最低价")
    close: float = Field(..., description="收盘价")
    vol: float = Field(..., description="成交量")
    amount: float = Field(default=0.0, description="成交额")
    pct_chg: float = Field(default=0.0, description="涨跌幅（%）")

    model_config = {"frozen": True}
