"""
概念图谱同步相关 DTO
"""

from pydantic import BaseModel, Field


class ConceptGraphSyncDTO(BaseModel):
    """
    概念图谱同步 DTO
    用于从 PostgreSQL 读取概念数据并同步到 Neo4j
    """

    code: str = Field(..., description="概念板块代码")
    name: str = Field(..., description="概念板块名称")
    stock_third_codes: list[str] = Field(
        default_factory=list, description="该概念下的股票代码列表（系统标准格式）"
    )
