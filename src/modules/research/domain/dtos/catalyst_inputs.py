from typing import List, Optional

from pydantic import BaseModel


class CatalystStockOverview(BaseModel):
    """
    催化剂分析所需的股票基础概览信息 (Input DTO)
    复用 MacroStockOverview 的字段集，但独立定义
    """

    stock_name: str
    industry: str
    third_code: str


class CatalystSearchResultItem(BaseModel):
    """
    单条催化剂搜索结果
    """

    title: str
    url: str
    snippet: str
    summary: Optional[str] = None
    site_name: Optional[str] = None
    published_date: Optional[str] = None


class CatalystSearchResult(BaseModel):
    """
    某一维度下的催化剂搜索结果集合
    """

    dimension_topic: str  # 搜索维度主题，如 "公司重大事件"
    items: List[CatalystSearchResultItem]
