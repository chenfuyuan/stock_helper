"""
估值快照 DTO，与 User Prompt 模板占位符一一对应。
快照构建器将估值输入与预计算指标转为 ValuationSnapshotDTO。
"""

from pydantic import BaseModel, Field

from src.modules.research.domain.dtos.types import PlaceholderValue


class ValuationSnapshotDTO(BaseModel):
    """
    估值快照 DTO，与 User Prompt 模板占位符一一对应。
    包含股票信息、最新市场数据、预计算的估值模型指标、财务质量指标。
    """

    stock_name: str = Field(default="", description="股票名称")
    stock_code: str = Field(default="", description="股票代码")
    current_date: str = Field(default="", description="分析日期")
    industry: str = Field(default="", description="所属行业")

    current_price: PlaceholderValue = Field(default="N/A", description="当前价格（元）")
    total_mv: PlaceholderValue = Field(default="N/A", description="总市值（亿元）")
    pe_ttm: PlaceholderValue = Field(default="N/A", description="市盈率TTM")
    pe_percentile: PlaceholderValue = Field(default="N/A", description="PE 历史分位点（0-100）")
    pb: PlaceholderValue = Field(default="N/A", description="市净率")
    pb_percentile: PlaceholderValue = Field(default="N/A", description="PB 历史分位点（0-100）")
    ps_ttm: PlaceholderValue = Field(default="N/A", description="市销率TTM")
    ps_percentile: PlaceholderValue = Field(default="N/A", description="PS 历史分位点（0-100）")
    dv_ratio: PlaceholderValue = Field(default="N/A", description="股息率（%）")

    roe: PlaceholderValue = Field(default="N/A", description="净资产收益率（使用 roe_waa）")
    gros_profit_margin: PlaceholderValue = Field(default="N/A", description="毛利率（%）")
    gross_margin_trend: str = Field(default="N/A", description="毛利率趋势描述")
    net_profit_margin: PlaceholderValue = Field(default="N/A", description="净利率（%）")
    debt_to_assets: PlaceholderValue = Field(default="N/A", description="资产负债率（%）")

    growth_rate_avg: PlaceholderValue = Field(default="N/A", description="4 季平均利润增速（%）")
    peg_ratio: PlaceholderValue = Field(default="N/A", description="PEG 比率")
    graham_intrinsic_val: PlaceholderValue = Field(
        default="N/A", description="格雷厄姆内在价值（元）"
    )
    graham_safety_margin: PlaceholderValue = Field(default="N/A", description="安全边际（%）")
