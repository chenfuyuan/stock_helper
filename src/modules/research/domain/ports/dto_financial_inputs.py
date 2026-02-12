"""
Research 模块内使用的财务输入型 DTO（与下游模块解耦）。
Adapter 将 data_engineering 的 FinanceIndicatorDTO 转为 FinanceRecordInput。
快照构建器将多期 FinanceRecordInput 转为 FinancialSnapshotDTO（与 User Prompt 占位符一一对应）。
"""
from datetime import date
from typing import Optional, Union

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


# 用于占位符填充：标量可传 float/int，序列传 list，N/A 用 "N/A" 字符串
PlaceholderValue = Union[float, int, str, list[float], list[int], list[str]]


class FinancialSnapshotDTO(BaseModel):
    """
    财务快照 DTO，与 User Prompt 模板占位符一一对应。
    包含静态快照（当期关键指标）与历史趋势序列。
    """

    # Target Asset
    symbol: str = ""
    report_period: str = ""
    source: str = "tushare"

    # A. 盈利能力
    gross_margin: PlaceholderValue = "N/A"
    netprofit_margin: PlaceholderValue = "N/A"
    roe_waa: PlaceholderValue = "N/A"
    roic: PlaceholderValue = "N/A"

    # B. 每股含金量
    eps: PlaceholderValue = "N/A"
    eps_deducted: PlaceholderValue = "N/A"
    ocfps: PlaceholderValue = "N/A"
    fcff_ps: PlaceholderValue = "N/A"
    quality_ratio: PlaceholderValue = "N/A"

    # C. 资产负债与流动性
    current_ratio: PlaceholderValue = "N/A"
    quick_ratio: PlaceholderValue = "N/A"
    debt_to_assets: PlaceholderValue = "N/A"
    interestdebt: PlaceholderValue = "N/A"
    netdebt: PlaceholderValue = "N/A"

    # D. 运营效率
    invturn_days: PlaceholderValue = "N/A"
    arturn_days: PlaceholderValue = "N/A"
    assets_turn: PlaceholderValue = "N/A"

    # 历史趋势（JSON 序列化后填入模板）
    quarter_list: list[str] = Field(default_factory=list)
    revenue_growth_series: list[PlaceholderValue] = Field(default_factory=list)
    profit_growth_series: list[PlaceholderValue] = Field(default_factory=list)
    gross_margin_series: list[PlaceholderValue] = Field(default_factory=list)
    roic_series: list[PlaceholderValue] = Field(default_factory=list)
    fcff_series: list[PlaceholderValue] = Field(default_factory=list)
    invturn_days_series: list[PlaceholderValue] = Field(default_factory=list)
    arturn_days_series: list[PlaceholderValue] = Field(default_factory=list)
