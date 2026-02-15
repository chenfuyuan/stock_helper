"""
Market Insight Application 层 DTO 定义
用于对外暴露的应用层接口
"""

from datetime import date
from typing import List

from pydantic import BaseModel, Field


class ConceptHeatDTO(BaseModel):
    """概念热度 DTO"""

    trade_date: date = Field(..., description="交易日期")
    concept_code: str = Field(..., description="概念板块代码")
    concept_name: str = Field(..., description="概念板块名称")
    avg_pct_chg: float = Field(..., description="等权平均涨跌幅（百分比）")
    stock_count: int = Field(..., description="成分股总数")
    up_count: int = Field(..., description="上涨家数")
    down_count: int = Field(..., description="下跌家数")
    limit_up_count: int = Field(..., description="涨停家数")
    total_amount: float = Field(..., description="板块成交额合计")


class LimitUpStockDTO(BaseModel):
    """涨停股 DTO"""

    trade_date: date = Field(..., description="交易日期")
    third_code: str = Field(..., description="股票代码")
    stock_name: str = Field(..., description="股票名称")
    pct_chg: float = Field(..., description="涨跌幅（百分比）")
    close: float = Field(..., description="收盘价")
    amount: float = Field(..., description="成交额")
    concept_codes: List[str] = Field(..., description="所属概念板块代码列表")
    concept_names: List[str] = Field(..., description="所属概念板块名称列表")
    limit_type: str = Field(..., description="涨停类型")


class DailyReportResult(BaseModel):
    """每日复盘报告结果 DTO"""

    trade_date: date = Field(..., description="交易日期")
    concept_count: int = Field(..., description="参与计算的概念数量")
    limit_up_count: int = Field(..., description="涨停股数量")
    report_path: str = Field(..., description="生成的 Markdown 文件路径")
    elapsed_seconds: float = Field(..., description="总执行耗时（秒）")
