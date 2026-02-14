"""
搜索维度配置数据类。

定义每个搜索维度的配置：维度主题、查询模板、返回条数、时效过滤。
用于驱动宏观情报员和催化剂侦探的搜索循环，避免硬编码。
"""
from typing import Literal
from pydantic import BaseModel, Field


class SearchDimensionConfig(BaseModel):
    """
    搜索维度配置。
    
    Attributes:
        topic: 维度主题名称（用于日志和上下文构建）
        query_template: 查询模板，支持 {stock_name}、{industry}、{year} 占位符
        count: 返回结果条数（4-10）
        freshness: 时效过滤，可选值：oneDay/oneWeek/oneMonth/oneYear/noLimit
    """
    topic: str = Field(..., description="维度主题名称")
    query_template: str = Field(..., description="查询模板，支持占位符")
    count: int = Field(..., ge=4, le=10, description="返回结果条数")
    freshness: Literal["oneDay", "oneWeek", "oneMonth", "oneYear", "noLimit"] = Field(
        ..., description="时效过滤"
    )
