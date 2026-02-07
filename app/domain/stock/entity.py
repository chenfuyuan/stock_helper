from typing import Optional
from datetime import date
from pydantic import Field, ConfigDict
from app.domain.base_entity import BaseEntity

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
    market: Optional[str] = Field(None, description="市场类型 (主板/创业板/科创板/CDR)")
    list_date: Optional[date] = Field(None, description="上市日期")
    
    # 新增字段
    fullname: Optional[str] = Field(None, description="股票全称")
    enname: Optional[str] = Field(None, description="英文全称")
    cnspell: Optional[str] = Field(None, description="拼音缩写")
    exchange: Optional[str] = Field(None, description="交易所代码")
    curr_type: Optional[str] = Field(None, description="交易货币")
    list_status: Optional[str] = Field(None, description="上市状态 L上市 D退市 P暂停上市")
    delist_date: Optional[date] = Field(None, description="退市日期")
    is_hs: Optional[str] = Field(None, description="是否沪深港通标的，N否 H沪股通 S深股通")
    
    # 来源标记
    source: Optional[str] = Field("tushare", description="数据来源")
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "third_code": "000001.SZ",
                "symbol": "000001",
                "name": "平安银行",
                "area": "深圳",
                "industry": "银行",
                "market": "主板",
                "list_date": "1991-04-03",
                "source": "tushare"
            }
        }
    )
