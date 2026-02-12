"""
Research 模块内使用的单期财务输入型 DTO。
Adapter 将 data_engineering 的 FinanceIndicatorDTO 转为 FinanceRecordInput。
"""
from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class FinanceRecordInput(BaseModel):
    """
    单期财务数据输入，用于快照构建与 Prompt 填充。
    由 data_engineering 的 FinanceIndicatorDTO 转入。
    """

    end_date: date
    ann_date: date
    third_code: str
    source: str = "tushare"

    gross_margin: Optional[float] = None
    netprofit_margin: Optional[float] = None
    roe_waa: Optional[float] = None
    roic: Optional[float] = None

    eps: Optional[float] = None
    bps: Optional[float] = None
    profit_dedt: Optional[float] = None
    ocfps: Optional[float] = None
    fcff_ps: Optional[float] = None

    current_ratio: Optional[float] = None
    quick_ratio: Optional[float] = None
    debt_to_assets: Optional[float] = None
    interestdebt: Optional[float] = None
    netdebt: Optional[float] = None

    invturn_days: Optional[float] = None
    arturn_days: Optional[float] = None
    assets_turn: Optional[float] = None

    total_revenue_ps: Optional[float] = None
    fcff: Optional[float] = None
