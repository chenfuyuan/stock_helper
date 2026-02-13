"""
财务快照 DTO，与 User Prompt 模板占位符一一对应。
快照构建器将多期 FinanceRecordInput 转为 FinancialSnapshotDTO。
"""
from pydantic import BaseModel, Field

from src.modules.research.domain.dtos.types import PlaceholderValue


class FinancialSnapshotDTO(BaseModel):
    """
    财务快照 DTO，与 User Prompt 模板占位符一一对应。
    包含静态快照（当期关键指标）与历史趋势序列。
    """

    symbol: str = ""
    report_period: str = ""
    source: str = "tushare"

    gross_margin: PlaceholderValue = "N/A"
    netprofit_margin: PlaceholderValue = "N/A"
    roe_waa: PlaceholderValue = "N/A"
    roic: PlaceholderValue = "N/A"

    eps: PlaceholderValue = "N/A"
    eps_deducted: PlaceholderValue = "N/A"  # 注意：实际填入的是 profit_dedt（扣非净利润总额），非每股扣非收益
    bps: PlaceholderValue = "N/A"
    ocfps: PlaceholderValue = "N/A"
    fcff_ps: PlaceholderValue = "N/A"
    quality_ratio: PlaceholderValue = "N/A"

    current_ratio: PlaceholderValue = "N/A"
    quick_ratio: PlaceholderValue = "N/A"
    debt_to_assets: PlaceholderValue = "N/A"
    interestdebt: PlaceholderValue = "N/A"
    netdebt: PlaceholderValue = "N/A"

    invturn_days: PlaceholderValue = "N/A"
    arturn_days: PlaceholderValue = "N/A"
    assets_turn: PlaceholderValue = "N/A"

    quarter_list: list[str] = Field(default_factory=list)
    revenue_growth_series: list[PlaceholderValue] = Field(default_factory=list)
    profit_growth_series: list[PlaceholderValue] = Field(default_factory=list)
    gross_margin_series: list[PlaceholderValue] = Field(default_factory=list)
    roic_series: list[PlaceholderValue] = Field(default_factory=list)
    fcff_series: list[PlaceholderValue] = Field(default_factory=list)
    invturn_days_series: list[PlaceholderValue] = Field(default_factory=list)
    arturn_days_series: list[PlaceholderValue] = Field(default_factory=list)
