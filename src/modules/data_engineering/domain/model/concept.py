from pydantic import Field

from src.shared.domain.base_entity import BaseEntity


class Concept(BaseEntity):
    """
    概念板块领域实体
    表示一个概念题材板块（如"低空经济"、"人形机器人"）
    """

    code: str = Field(..., description="概念板块代码（如 BK0493），唯一标识")
    name: str = Field(..., description="概念板块名称（如 低空经济）")


class ConceptStock(BaseEntity):
    """
    概念-股票映射领域实体
    表示概念板块与股票的关联关系（多对多）
    """

    concept_code: str = Field(..., description="所属概念板块代码")
    third_code: str = Field(..., description="股票代码，系统标准格式（如 000001.SZ）")
    stock_name: str = Field(..., description="股票名称")
