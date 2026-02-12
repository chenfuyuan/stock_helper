"""
Research 模块内使用的估值输入型 DTO。
Adapter 将 data_engineering 的各类 DTO 转为 Research 内部的估值输入。
"""
from datetime import date
from typing import Optional

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
