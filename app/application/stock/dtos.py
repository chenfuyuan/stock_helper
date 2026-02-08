from typing import Optional
from pydantic import BaseModel, Field
from app.domain.stock.entities import StockInfo, StockDaily

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
