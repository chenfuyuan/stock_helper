"""
涨停股票领域实体
"""

from datetime import date
from typing import List

from pydantic import BaseModel, Field

from src.modules.market_insight.domain.model.enums import LimitType


class Concept(BaseModel):
    """概念对象"""
    code: str = Field(..., description="概念代码")
    name: str = Field(..., description="概念名称")


class LimitUpStock(BaseModel):
    """涨停股票实体"""
    
    trade_date: date = Field(..., description="交易日期")
    third_code: str = Field(..., description="股票代码")
    stock_name: str = Field(..., description="股票名称")
    pct_chg: float = Field(..., description="涨跌幅（百分比）")
    close: float = Field(..., description="收盘价")
    amount: float = Field(..., description="成交额")
    concepts: List[Concept] = Field(..., description="所属概念板块对象列表")
    limit_type: LimitType = Field(..., description="涨停类型")
    
    @property
    def concept_codes(self) -> List[str]:
        """获取概念代码列表（向后兼容）"""
        return [c.code for c in self.concepts]
    
    @property
    def concept_names(self) -> List[str]:
        """获取概念名称列表（向后兼容）"""
        return [c.name for c in self.concepts]
