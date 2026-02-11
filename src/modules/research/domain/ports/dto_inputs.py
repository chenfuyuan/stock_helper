"""
Research 模块内使用的输入型 DTO（与下游模块解耦）。
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
