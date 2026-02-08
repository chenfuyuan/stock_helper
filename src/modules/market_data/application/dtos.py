from typing import Optional
from pydantic import BaseModel, Field
from src.modules.market_data.domain.entities import StockInfo, StockDaily

class StockBasicInfoDTO(BaseModel):
    """
    股票基础信息聚合 DTO
    """
    info: StockInfo = Field(..., description="股票基础信息")
    daily: Optional[StockDaily] = Field(None, description="最新日线行情")

class SyncStockOutput(BaseModel):
    """
    股票同步用例输出 DTO
    """
    status: str
    synced_count: int
    message: str

class StockFullDTO(BaseModel):
    """
    完整的股票数据包，用于智能体分析
    """
    price_info: dict = Field(..., description="日线数据")
    financial_info: dict = Field(..., description="财务数据")
    company_info: dict = Field(..., description="公司基本信息")
