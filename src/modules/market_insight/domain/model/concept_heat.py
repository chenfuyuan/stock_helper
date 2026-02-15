"""
概念板块热度领域实体
"""

from datetime import date

from pydantic import BaseModel, Field


class ConceptHeat(BaseModel):
    """概念板块热度实体"""
    
    trade_date: date = Field(..., description="交易日期")
    concept_code: str = Field(..., description="概念板块代码")
    concept_name: str = Field(..., description="概念板块名称")
    avg_pct_chg: float = Field(..., description="等权平均涨跌幅（百分比）")
    stock_count: int = Field(..., description="成分股总数")
    up_count: int = Field(..., description="上涨家数")
    down_count: int = Field(..., description="下跌家数")
    limit_up_count: int = Field(..., description="涨停家数")
    total_amount: float = Field(..., description="板块成交额合计")
