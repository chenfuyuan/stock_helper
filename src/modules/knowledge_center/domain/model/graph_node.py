"""
图谱节点领域实体。

定义 Stock、Industry、Area、Market、Exchange 节点的 Pydantic 模型。
"""

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class StockNode(BaseModel):
    """
    Stock 节点实体。
    
    包含股票基本信息与可选的财务快照属性。
    """

    third_code: str = Field(..., description="第三方系统代码（如 Tushare ts_code），作为唯一标识")
    symbol: str = Field(..., description="股票代码")
    name: str = Field(..., description="股票名称")
    fullname: Optional[str] = Field(None, description="股票全称")
    list_date: Optional[date] = Field(None, description="上市日期")
    list_status: Optional[str] = Field(None, description="上市状态")
    curr_type: Optional[str] = Field(None, description="交易货币")
    
    # 可选财务快照字段（最新一期）
    roe: Optional[float] = Field(None, description="净资产收益率")
    roa: Optional[float] = Field(None, description="总资产报酬率")
    gross_margin: Optional[float] = Field(None, description="毛利率")
    debt_to_assets: Optional[float] = Field(None, description="资产负债率")
    pe_ttm: Optional[float] = Field(None, description="市盈率TTM")
    pb: Optional[float] = Field(None, description="市净率")
    total_mv: Optional[float] = Field(None, description="总市值")


class IndustryNode(BaseModel):
    """
    Industry 节点实体。
    
    代表行业维度节点。
    """

    name: str = Field(..., description="行业名称，作为唯一标识")


class AreaNode(BaseModel):
    """
    Area 节点实体。
    
    代表地域维度节点。
    """

    name: str = Field(..., description="地域名称，作为唯一标识")


class MarketNode(BaseModel):
    """
    Market 节点实体。
    
    代表市场类型维度节点（如主板、创业板）。
    """

    name: str = Field(..., description="市场名称，作为唯一标识")


class ExchangeNode(BaseModel):
    """
    Exchange 节点实体。
    
    代表交易所维度节点（如 SSE、SZSE）。
    """

    name: str = Field(..., description="交易所名称，作为唯一标识")
