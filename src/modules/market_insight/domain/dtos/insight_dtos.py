"""
Market Insight 领域层 DTO 定义
用于 Port 接口与领域服务之间的数据传递
"""

from datetime import date
from typing import List

from pydantic import BaseModel, Field


class ConceptStockDTO(BaseModel):
    """概念成分股 DTO"""
    
    third_code: str = Field(..., description="股票代码")
    stock_name: str = Field(..., description="股票名称")


class ConceptWithStocksDTO(BaseModel):
    """带成分股列表的概念 DTO"""
    
    code: str = Field(..., description="概念板块代码")
    name: str = Field(..., description="概念板块名称")
    stocks: List[ConceptStockDTO] = Field(..., description="成分股列表")


class StockDailyDTO(BaseModel):
    """股票日线 DTO"""
    
    third_code: str = Field(..., description="股票代码")
    stock_name: str = Field(..., description="股票名称")
    trade_date: date = Field(..., description="交易日期")
    close: float = Field(..., description="收盘价")
    pct_chg: float = Field(..., description="涨跌幅（百分比）")
    amount: float = Field(..., description="成交额")


class ConceptInfoDTO(BaseModel):
    """概念信息 DTO"""
    
    code: str = Field(..., description="概念代码")
    name: str = Field(..., description="概念名称")
