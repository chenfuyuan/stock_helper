"""
概念节点领域实体
"""

from pydantic import Field

from src.shared.domain.base_entity import BaseEntity


class ConceptNode(BaseEntity):
    """
    概念题材节点实体
    表示图谱中的一个概念板块节点（如"低空经济"、"人形机器人"）
    """

    code: str = Field(..., description="概念板块代码（如 BK0493），唯一标识")
    name: str = Field(..., description="概念板块名称（如 低空经济）")
