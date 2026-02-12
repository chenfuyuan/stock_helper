"""
Research 模块内使用的估值输入型 DTO（与下游模块解耦）。
Adapter 将 data_engineering 的各类 DTO 转为 Research 内部的估值输入 DTO。
快照构建器将这些输入 DTO 转为 ValuationSnapshotDTO（与 User Prompt 占位符一一对应）。
"""
from datetime import date
from typing import Optional, Union

from pydantic import BaseModel, Field


class StockOverviewInput(BaseModel):
    """
    股票概览输入，包含股票基础信息与最新市场估值数据。
    由 data_engineering 的 GetStockBasicInfoUseCase 返回的 StockInfo + StockDaily 转入。
    """

    stock_name: str = Field(..., description="股票名称")
    industry: str = Field(..., description="所属行业")
    third_code: str = Field(..., description="第三方代码（如 000001.SZ）")
    current_price: float = Field(..., description="当前收盘价")
    total_mv: Optional[float] = Field(None, description="总市值（万元）")
    pe_ttm: Optional[float] = Field(None, description="市盈率TTM")
    pb: Optional[float] = Field(None, description="市净率")
    ps_ttm: Optional[float] = Field(None, description="市销率TTM")
    dv_ratio: Optional[float] = Field(None, description="股息率")


class ValuationDailyInput(BaseModel):
    """
    单日估值输入，用于历史分位点计算。
    由 data_engineering 的 ValuationDailyDTO 转入。
    """

    trade_date: date = Field(..., description="交易日期")
    close: float = Field(..., description="收盘价")
    pe_ttm: Optional[float] = Field(None, description="市盈率TTM")
    pb: Optional[float] = Field(None, description="市净率")
    ps_ttm: Optional[float] = Field(None, description="市销率TTM")


# 用于占位符填充：标量可传 float/int，序列传 list，N/A 用 "N/A" 字符串
PlaceholderValue = Union[float, int, str]


class ValuationSnapshotDTO(BaseModel):
    """
    估值快照 DTO，与 User Prompt 模板占位符一一对应。
    包含股票信息、最新市场数据、预计算的估值模型指标、财务质量指标。
    """

    # 股票信息
    stock_name: str = Field(default="", description="股票名称")
    stock_code: str = Field(default="", description="股票代码")
    current_date: str = Field(default="", description="分析日期")
    industry: str = Field(default="", description="所属行业")

    # 市场相对估值
    current_price: PlaceholderValue = Field(default="N/A", description="当前价格（元）")
    total_mv: PlaceholderValue = Field(default="N/A", description="总市值（亿元）")
    pe_ttm: PlaceholderValue = Field(default="N/A", description="市盈率TTM")
    pe_percentile: PlaceholderValue = Field(default="N/A", description="PE 历史分位点（0-100）")
    pb: PlaceholderValue = Field(default="N/A", description="市净率")
    pb_percentile: PlaceholderValue = Field(default="N/A", description="PB 历史分位点（0-100）")
    ps_ttm: PlaceholderValue = Field(default="N/A", description="市销率TTM")
    ps_percentile: PlaceholderValue = Field(default="N/A", description="PS 历史分位点（0-100）")
    dv_ratio: PlaceholderValue = Field(default="N/A", description="股息率（%）")

    # 基本面质量体检
    roe: PlaceholderValue = Field(default="N/A", description="净资产收益率（使用 roe_waa）")
    gros_profit_margin: PlaceholderValue = Field(default="N/A", description="毛利率（%）")
    gross_margin_trend: str = Field(default="N/A", description="毛利率趋势描述")
    net_profit_margin: PlaceholderValue = Field(default="N/A", description="净利率（%）")
    debt_to_assets: PlaceholderValue = Field(default="N/A", description="资产负债率（%）")

    # 预计算估值模型
    growth_rate_avg: PlaceholderValue = Field(default="N/A", description="4 季平均利润增速（%）")
    peg_ratio: PlaceholderValue = Field(default="N/A", description="PEG 比率")
    graham_intrinsic_val: PlaceholderValue = Field(default="N/A", description="格雷厄姆内在价值（元）")
    graham_safety_margin: PlaceholderValue = Field(default="N/A", description="安全边际（%）")
