"""
图谱 API 响应 DTO。

定义 REST 层使用的请求与响应数据结构。
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field


class SyncGraphRequest(BaseModel):
    """
    同步图谱请求 DTO。
    
    用于 POST /sync 端点。
    """

    mode: Literal["full", "incremental"] = Field(..., description="同步模式：full（全量）或 incremental（增量）")  # noqa: E501
    target: Literal["stock", "concept", "all"] = Field(
        "stock",
        description="同步目标：stock（股票）、concept（概念）或 all（全部），默认 stock",
    )
    third_codes: Optional[list[str]] = Field(
        None,
        description="增量同步时可选的股票代码列表；为空时按 window_days 自动确定范围",
    )
    include_finance: bool = Field(False, description="是否包含财务快照数据")
    batch_size: int = Field(500, description="批量大小")
    window_days: int = Field(3, ge=1, description="增量自动模式的时间窗口天数")
    skip: int = Field(0, description="全量同步时跳过前 N 条记录")
    limit: int = Field(10000, description="全量或自动增量模式下的扫描数量上限")


class SyncGraphResponse(BaseModel):
    """
    同步图谱响应 DTO。
    
    返回同步结果摘要。
    """

    total: int = Field(..., description="总处理数量")
    success: int = Field(..., description="成功数量")
    failed: int = Field(..., description="失败数量")
    duration_ms: float = Field(..., description="耗时（毫秒）")
    error_details: list[str] = Field(default_factory=list, description="失败记录的错误详情列表")


class StockNeighborResponse(BaseModel):
    """
    同维度股票响应 DTO。
    
    用于 GET /stocks/{third_code}/neighbors 端点。
    """

    third_code: str = Field(..., description="第三方代码")
    name: str = Field(..., description="股票名称")
    industry: Optional[str] = Field(None, description="所属行业")
    area: Optional[str] = Field(None, description="所在地域")
    market: Optional[str] = Field(None, description="市场类型")
    exchange: Optional[str] = Field(None, description="交易所")


class GraphNodeResponse(BaseModel):
    """
    图谱节点响应 DTO。
    """

    label: str = Field(..., description="节点标签")
    id: str = Field(..., description="节点唯一标识符")
    properties: dict = Field(default_factory=dict, description="节点属性字典")


class GraphRelationshipResponse(BaseModel):
    """
    图谱关系响应 DTO。
    """

    source_id: str = Field(..., description="源节点标识符")
    target_id: str = Field(..., description="目标节点标识符")
    relationship_type: str = Field(..., description="关系类型")


class StockGraphResponse(BaseModel):
    """
    个股关系网络响应 DTO。
    
    用于 GET /stocks/{third_code}/graph 端点。
    """

    nodes: list[GraphNodeResponse] = Field(..., description="节点列表")
    relationships: list[GraphRelationshipResponse] = Field(..., description="关系列表")


class SyncStocksFullRequest(BaseModel):
    """
    股票全量同步请求 DTO。
    
    用于 POST /sync/stocks/full 端点。
    """

    include_finance: bool = Field(False, description="是否包含财务快照数据")
    batch_size: int = Field(500, description="批量大小")
    skip: int = Field(0, description="跳过前 N 条记录")
    limit: int = Field(10000, description="查询数量上限")


class SyncStocksIncrementalRequest(BaseModel):
    """
    股票增量同步请求 DTO。
    
    用于 POST /sync/stocks/incremental 端点。
    """

    third_codes: Optional[list[str]] = Field(
        None,
        description="股票代码列表；为空时按时间窗口自动确定",
    )
    include_finance: bool = Field(False, description="是否包含财务快照数据")
    batch_size: int = Field(500, description="批量大小")
    window_days: int = Field(3, ge=1, description="自动模式下时间窗口天数")
    limit: int = Field(10000, description="自动模式下扫描上限")


class SyncConceptsRequest(BaseModel):
    """
    概念同步请求 DTO。
    
    用于 POST /sync/concepts 端点。
    """

    batch_size: int = Field(500, description="批量大小")


class SyncAllRequest(BaseModel):
    """
    全部同步请求 DTO。
    
    用于 POST /sync/all 端点。
    """

    mode: Literal["full", "incremental"] = Field(..., description="股票同步模式：full（全量）或 incremental（增量）")
    include_finance: bool = Field(False, description="是否包含财务快照数据")
    batch_size: int = Field(500, description="批量大小")
    third_codes: Optional[list[str]] = Field(
        None,
        description="股票代码列表（仅 mode=incremental 时有效）",
    )
    window_days: int = Field(3, ge=1, description="自动模式下时间窗口天数（仅 mode=incremental 时有效）")
    skip: int = Field(0, description="跳过前 N 条记录（仅 mode=full 时有效）")
    limit: int = Field(10000, description="扫描/查询数量上限")
