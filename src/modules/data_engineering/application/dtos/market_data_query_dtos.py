"""
AkShare 市场数据 Query 返回的 DTO。

供涨停池、炸板池、龙虎榜、昨日涨停、板块资金流向等 Query 返回，
避免跨模块暴露 Domain Entity。字段与对应 Entity 的对外可见字段一致。
"""

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class LimitUpPoolDTO(BaseModel):
    """涨停池 DTO——仅暴露涨停池分析所需字段。"""

    trade_date: date = Field(..., description="交易日期")
    third_code: str = Field(..., description="股票代码（系统标准格式，如 000001.SZ）")
    stock_name: str = Field(..., description="股票名称")
    pct_chg: float = Field(..., description="涨跌幅（百分比）")
    close: float = Field(..., description="最新价")
    amount: float = Field(..., description="成交额")
    turnover_rate: float = Field(..., description="换手率")
    consecutive_boards: int = Field(..., description="连板天数（首板为 1）")
    first_limit_up_time: Optional[str] = Field(None, description="首次封板时间")
    last_limit_up_time: Optional[str] = Field(None, description="最后封板时间")
    industry: str = Field(..., description="所属行业")

    model_config = {"frozen": True}


class BrokenBoardDTO(BaseModel):
    """炸板池 DTO——仅暴露炸板池分析所需字段。"""

    trade_date: date = Field(..., description="交易日期")
    third_code: str = Field(..., description="股票代码（系统标准格式，如 000001.SZ）")
    stock_name: str = Field(..., description="股票名称")
    pct_chg: float = Field(..., description="涨跌幅（百分比）")
    close: float = Field(..., description="最新价")
    amount: float = Field(..., description="成交额")
    turnover_rate: float = Field(..., description="换手率")
    open_count: int = Field(..., description="开板次数")
    first_limit_up_time: Optional[str] = Field(None, description="首次封板时间")
    last_open_time: Optional[str] = Field(None, description="最后开板时间")
    industry: str = Field(..., description="所属行业")

    model_config = {"frozen": True}


class DragonTigerDTO(BaseModel):
    """龙虎榜 DTO——仅暴露龙虎榜分析所需字段。"""

    trade_date: date = Field(..., description="交易日期")
    third_code: str = Field(..., description="股票代码（系统标准格式，如 000001.SZ）")
    stock_name: str = Field(..., description="股票名称")
    pct_chg: float = Field(..., description="涨跌幅（百分比）")
    close: float = Field(..., description="收盘价")
    reason: str = Field(..., description="上榜原因")
    net_amount: float = Field(..., description="龙虎榜净买入额")
    buy_amount: float = Field(..., description="买入总额")
    sell_amount: float = Field(..., description="卖出总额")
    buy_seats: list[dict] = Field(default_factory=list, description="买入席位详情")
    sell_seats: list[dict] = Field(default_factory=list, description="卖出席位详情")

    model_config = {"frozen": True}


class PreviousLimitUpDTO(BaseModel):
    """昨日涨停表现 DTO——仅暴露昨日涨停分析所需字段。"""

    trade_date: date = Field(..., description="交易日期（表现观察日）")
    third_code: str = Field(..., description="股票代码（系统标准格式，如 000001.SZ）")
    stock_name: str = Field(..., description="股票名称")
    pct_chg: float = Field(..., description="今日涨跌幅（百分比）")
    close: float = Field(..., description="最新价")
    amount: float = Field(..., description="成交额")
    turnover_rate: float = Field(..., description="换手率")
    yesterday_consecutive_boards: int = Field(..., description="昨日连板天数")
    industry: str = Field(..., description="所属行业")

    model_config = {"frozen": True}


class SectorCapitalFlowDTO(BaseModel):
    """板块资金流向 DTO——仅暴露资金流向分析所需字段。"""

    trade_date: date = Field(..., description="交易日期")
    sector_name: str = Field(..., description="板块名称")
    sector_type: str = Field(..., description="板块类型（如'概念资金流'）")
    net_amount: float = Field(..., description="净流入额（万元）")
    inflow_amount: float = Field(..., description="流入额（万元）")
    outflow_amount: float = Field(..., description="流出额（万元）")
    pct_chg: float = Field(..., description="板块涨跌幅（百分比）")

    model_config = {"frozen": True}
