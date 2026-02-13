"""
宏观情报员输入型 DTO。

定义宏观分析所需的股票概览与搜索结果数据结构。
Adapter 将 data_engineering 的股票信息 + llm_platform 的搜索结果转为这些 DTO。
"""
from typing import List, Optional

from pydantic import BaseModel, Field


class MacroStockOverview(BaseModel):
    """
    宏观分析用的股票概览，仅包含宏观分析所需的基础信息。
    
    与估值建模师的 StockOverviewInput 不同，宏观情报员不需要价格/市值/估值数据，
    因此使用独立的 DTO，避免耦合到估值特定的数据结构。
    """

    stock_name: str = Field(..., description="股票名称")
    industry: str = Field(..., description="所属行业")
    third_code: str = Field(..., description="第三方代码（如 000001.SZ）")


class MacroSearchResultItem(BaseModel):
    """
    单条宏观搜索结果条目。
    
    从 llm_platform 的 WebSearchResponse 中映射而来，
    包含搜索结果的标题、URL、摘要等信息，用于构建宏观上下文。
    """

    title: str = Field(..., description="搜索结果标题")
    url: str = Field(..., description="搜索结果 URL")
    snippet: str = Field(..., description="搜索结果摘要片段")
    summary: Optional[str] = Field(None, description="AI 生成的摘要（由搜索 API 提供）")
    site_name: Optional[str] = Field(None, description="来源站点名称")
    published_date: Optional[str] = Field(None, description="发布日期")


class MacroSearchResult(BaseModel):
    """
    单个宏观维度的搜索结果集合。
    
    将搜索结果按宏观维度（货币政策、产业政策、宏观经济、行业景气）分组，
    每个维度的搜索结果独立存储，便于后续按维度构建上下文。
    """

    dimension_topic: str = Field(..., description="宏观维度主题（如'货币与流动性'、'产业政策'等）")
    items: List[MacroSearchResultItem] = Field(
        default_factory=list, description="该维度下的搜索结果条目列表"
    )
