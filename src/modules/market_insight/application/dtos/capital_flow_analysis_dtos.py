from datetime import date

from pydantic import BaseModel

from src.modules.market_insight.domain.dtos.capital_flow_dtos import (
    DragonTigerAnalysis,
    SectorCapitalFlowAnalysis,
)


class CapitalFlowAnalysisDTO(BaseModel):
    """资金流向分析汇总 DTO（应用层）"""
    
    trade_date: date
    dragon_tiger_analysis: DragonTigerAnalysis
    sector_capital_flow_analysis: SectorCapitalFlowAnalysis
