from datetime import date

from pydantic import Field

from src.shared.domain.base_entity import BaseEntity


class DragonTigerDetail(BaseEntity):
    """
    龙虎榜详情领域实体
    表示某交易日的龙虎榜记录（含席位详情）
    """

    trade_date: date = Field(..., description="交易日期")
    third_code: str = Field(..., description="股票代码（系统标准格式，如 000001.SZ）")
    stock_name: str = Field(..., description="股票名称")
    pct_chg: float = Field(..., description="涨跌幅（百分比）")
    close: float = Field(..., description="收盘价")
    reason: str = Field(..., description="上榜原因")
    net_amount: float = Field(..., description="龙虎榜净买入额")
    buy_amount: float = Field(..., description="买入总额")
    sell_amount: float = Field(..., description="卖出总额")
    buy_seats: list[dict] = Field(
        default_factory=list, description="买入席位详情（JSONB 存储）"
    )
    sell_seats: list[dict] = Field(
        default_factory=list, description="卖出席位详情（JSONB 存储）"
    )
