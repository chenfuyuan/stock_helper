from datetime import date
from typing import Optional
from pydantic import Field
from src.shared.domain.base_entity import BaseEntity

class StockDisclosure(BaseEntity):
    """
    股票财报披露计划实体
    Stock Financial Report Disclosure Plan Entity
    """
    third_code: str = Field(..., description="第三方系统代码 (如 Tushare 的 ts_code)")
    ann_date: Optional[date] = Field(None, description="最新披露公告日")
    end_date: date = Field(..., description="报告期")
    pre_date: Optional[date] = Field(None, description="预计披露日期")
    actual_date: Optional[date] = Field(None, description="实际披露日期")
