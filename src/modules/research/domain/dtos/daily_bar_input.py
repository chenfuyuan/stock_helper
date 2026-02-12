"""
Research 模块内使用的日线输入型 DTO。
Adapter 将 data_engineering 的 DailyBarDTO 转为 DailyBarInput。
"""
from datetime import date

from pydantic import BaseModel, Field


class DailyBarInput(BaseModel):
    """单日日线输入，用于指标计算与 Prompt 填充。"""

    trade_date: date
    open: float
    high: float
    low: float
    close: float
    vol: float
    amount: float = 0.0
    pct_chg: float = 0.0  # 涨跌幅（%），用于日涨跌幅展示，数据源无则传 0
