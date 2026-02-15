from pydantic import BaseModel, Field


class SectorCapitalFlowDTO(BaseModel):
    """
    板块资金流向数据 DTO
    用于从外部数据源获取板块资金流向数据
    """

    sector_name: str = Field(..., description="板块名称")
    sector_type: str = Field(..., description="板块类型（如'概念资金流'）")
    net_amount: float = Field(..., description="净流入额（万元）")
    inflow_amount: float = Field(..., description="流入额（万元）")
    outflow_amount: float = Field(..., description="流出额（万元）")
    pct_chg: float = Field(..., description="板块涨跌幅（百分比）")
