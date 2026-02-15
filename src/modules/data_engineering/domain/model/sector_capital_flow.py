from datetime import date

from pydantic import Field

from src.shared.domain.base_entity import BaseEntity


class SectorCapitalFlow(BaseEntity):
    """
    板块资金流向领域实体
    表示某交易日的板块资金流向记录
    """

    trade_date: date = Field(..., description="交易日期")
    sector_name: str = Field(..., description="板块名称")
    sector_type: str = Field(..., description="板块类型（如'概念资金流'）")
    net_amount: float = Field(..., description="净流入额（万元）")
    inflow_amount: float = Field(..., description="流入额（万元）")
    outflow_amount: float = Field(..., description="流出额（万元）")
    pct_chg: float = Field(..., description="板块涨跌幅（百分比）")
