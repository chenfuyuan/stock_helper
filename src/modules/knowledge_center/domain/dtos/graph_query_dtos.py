"""
图谱查询相关 DTO。

定义查询同维度股票与个股关系网络的输出 DTO。
"""

from typing import Any, Optional

from pydantic import BaseModel, Field


class StockNeighborDTO(BaseModel):
    """
    同维度股票邻居 DTO。
    
    用于返回与查询股票共享同一维度节点的其他股票信息。
    """

    third_code: str = Field(..., description="第三方代码")
    name: str = Field(..., description="股票名称")
    industry: Optional[str] = Field(None, description="所属行业")
    area: Optional[str] = Field(None, description="所在地域")
    market: Optional[str] = Field(None, description="市场类型")
    exchange: Optional[str] = Field(None, description="交易所")


class GraphNodeDTO(BaseModel):
    """
    图谱节点 DTO。
    
    通用节点表示，包含节点标签、标识符与属性字典。
    """

    label: str = Field(..., description="节点标签（STOCK/INDUSTRY/AREA/MARKET/EXCHANGE）")
    id: str = Field(..., description="节点唯一标识符（third_code 或 name）")
    properties: dict[str, Any] = Field(default_factory=dict, description="节点属性字典")


class GraphRelationshipDTO(BaseModel):
    """
    图谱关系 DTO。
    
    描述节点间的关系。
    """

    source_id: str = Field(..., description="源节点标识符")
    target_id: str = Field(..., description="目标节点标识符")
    relationship_type: str = Field(..., description="关系类型")


class StockGraphDTO(BaseModel):
    """
    个股关系网络 DTO。
    
    包含中心股票节点及其关联的维度节点和关系列表。
    """

    nodes: list[GraphNodeDTO] = Field(..., description="节点列表")
    relationships: list[GraphRelationshipDTO] = Field(..., description="关系列表")
