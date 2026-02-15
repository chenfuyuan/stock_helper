from pydantic import BaseModel


# ========== 输入 DTO（用于接收 DE 模块数据） ==========

class DragonTigerItemDTO(BaseModel):
    """龙虎榜单项 DTO（MI 领域层）"""
    
    third_code: str
    stock_name: str
    pct_chg: float
    close: float
    reason: str
    net_amount: float
    buy_amount: float
    sell_amount: float
    buy_seats: list[dict]
    sell_seats: list[dict]


class SectorCapitalFlowItemDTO(BaseModel):
    """板块资金流向单项 DTO（MI 领域层）"""
    
    sector_name: str
    sector_type: str
    net_amount: float
    inflow_amount: float
    outflow_amount: float
    pct_chg: float


# ========== 输出 DTO（分析结果） ==========

class DragonTigerStockSummary(BaseModel):
    """龙虎榜个股汇总"""
    
    third_code: str
    stock_name: str
    pct_chg: float
    net_amount: float
    reason: str


class DragonTigerAnalysis(BaseModel):
    """龙虎榜分析结果"""
    
    total_count: int
    total_net_buy: float
    top_net_buy_stocks: list[DragonTigerStockSummary]
    top_net_sell_stocks: list[DragonTigerStockSummary]
    institutional_activity: list[DragonTigerStockSummary]


class SectorCapitalFlowAnalysis(BaseModel):
    """板块资金流向分析结果"""
    
    total_sectors: int
    top_inflow_sectors: list[SectorCapitalFlowItemDTO]
    top_outflow_sectors: list[SectorCapitalFlowItemDTO]
    avg_pct_chg: float
