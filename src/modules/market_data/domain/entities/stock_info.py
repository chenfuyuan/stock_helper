from typing import Optional
from datetime import date
from pydantic import Field, ConfigDict
from src.shared.domain.base_entity import BaseEntity
from src.modules.market_data.domain.enums import ListStatus, IsHs, ExchangeType, MarketType

class StockInfo(BaseEntity):
    """
    股票基础信息领域实体
    Stock Basic Information Domain Entity
    """
    id: Optional[int] = Field(None, description="ID")
    third_code: str = Field(..., description="第三方系统代码 (如 Tushare 的 ts_code)")
    symbol: str = Field(..., description="股票代码 (如 000001)")
    name: str = Field(..., description="股票名称")
    area: Optional[str] = Field(None, description="所在地域")
    industry: Optional[str] = Field(None, description="所属行业")
    market: Optional[MarketType] = Field(None, description="市场类型")
    list_date: Optional[date] = Field(None, description="上市日期")
    
    # 新增字段
    fullname: Optional[str] = Field(None, description="股票全称")
    enname: Optional[str] = Field(None, description="英文全称")
    cnspell: Optional[str] = Field(None, description="拼音缩写")
    exchange: Optional[ExchangeType] = Field(None, description="交易所代码")
    curr_type: Optional[str] = Field(None, description="交易货币")
    list_status: Optional[ListStatus] = Field(None, description="上市状态")
    delist_date: Optional[date] = Field(None, description="退市日期")
    is_hs: Optional[IsHs] = Field(None, description="是否沪深港通标的")
    
    # 来源标记
    source: Optional[str] = Field("tushare", description="数据来源")

    # 财务数据同步状态
    last_finance_sync_date: Optional[date] = Field(None, description="上次财务数据同步时间")

    
    def is_active(self) -> bool:
        """是否处于上市状态"""
        return self.list_status == ListStatus.LISTED
        
    def is_connect_target(self) -> bool:
        """是否属于沪深港通标的"""
        return self.is_hs in (IsHs.HK, IsHs.SZ)
    
    model_config = ConfigDict(
        from_attributes=True,
        use_enum_values=True,  # 允许使用枚举值进行序列化
        json_schema_extra={
            "example": {
                "third_code": "000001.SZ",
                "symbol": "000001",
                "name": "平安银行",
                "area": "深圳",
                "industry": "银行",
                "market": "主板",
                "list_date": "1991-04-03",
                "list_status": "L",
                "source": "tushare"
            }
        }
    )
