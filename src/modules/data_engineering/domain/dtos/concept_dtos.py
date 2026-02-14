from pydantic import BaseModel, Field

from src.modules.data_engineering.domain.model.concept import ConceptStock


class ConceptInfoDTO(BaseModel):
    """
    概念板块基本信息 DTO
    用于从外部数据源获取概念列表
    """

    code: str = Field(..., description="概念板块代码（如 BK0493）")
    name: str = Field(..., description="概念板块名称（如 低空经济）")


class ConceptConstituentDTO(BaseModel):
    """
    概念成份股 DTO
    用于表示概念板块的成份股信息
    """

    stock_code: str = Field(..., description="股票代码，系统标准 third_code 格式（如 000001.SZ）")
    stock_name: str = Field(..., description="股票名称")


class ConceptWithStocksDTO(BaseModel):
    """
    概念及其成份股聚合 DTO
    用于聚合查询返回概念及其所有成份股
    """

    code: str = Field(..., description="概念板块代码")
    name: str = Field(..., description="概念板块名称")
    stocks: list[ConceptStock] = Field(default_factory=list, description="该概念下的成份股列表")
