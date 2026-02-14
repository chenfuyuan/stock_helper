"""
图谱同步相关 DTO。

定义从 data_engineering 模块转换而来的同步输入 DTO 与同步结果 DTO。
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field


class StockGraphSyncDTO(BaseModel):
    """
    Stock 图谱同步输入 DTO。
    
    由 data_engineering_adapter 从 StockInfo 和 StockFinance 转换而来，
    包含构建 Stock 节点及其维度关系所需的全部字段。
    """

    # 股票基本信息
    third_code: str = Field(..., description="第三方系统代码")
    symbol: str = Field(..., description="股票代码")
    name: str = Field(..., description="股票名称")
    fullname: Optional[str] = Field(None, description="股票全称")
    list_date: Optional[str] = Field(None, description="上市日期，格式 YYYYMMDD")
    list_status: Optional[str] = Field(None, description="上市状态")
    curr_type: Optional[str] = Field(None, description="交易货币")
    
    # 维度字段（用于构建关系）
    industry: Optional[str] = Field(None, description="所属行业")
    area: Optional[str] = Field(None, description="所在地域")
    market: Optional[str] = Field(None, description="市场类型")
    exchange: Optional[str] = Field(None, description="交易所代码")
    
    # 可选财务快照（最新一期）
    roe: Optional[float] = Field(None, description="净资产收益率")
    roa: Optional[float] = Field(None, description="总资产报酬率")
    gross_margin: Optional[float] = Field(None, description="毛利率")
    debt_to_assets: Optional[float] = Field(None, description="资产负债率")
    pe_ttm: Optional[float] = Field(None, description="市盈率TTM")
    pb: Optional[float] = Field(None, description="市净率")
    total_mv: Optional[float] = Field(None, description="总市值")


class DimensionDTO(BaseModel):
    """
    维度节点同步 DTO。

    用于独立批量写入 Industry/Area/Market/Exchange 维度节点。
    """

    label: Literal["INDUSTRY", "AREA", "MARKET", "EXCHANGE"] = Field(
        ...,
        description="维度标签",
    )
    name: str = Field(..., description="维度名称")


class SyncResult(BaseModel):
    """
    同步结果摘要 DTO。
    
    记录同步操作的成功/失败数量与耗时信息。
    """

    total: int = Field(..., description="总处理数量")
    success: int = Field(..., description="成功数量")
    failed: int = Field(..., description="失败数量")
    duration_ms: float = Field(..., description="耗时（毫秒）")
    error_details: list[str] = Field(default_factory=list, description="失败记录的错误详情列表")
