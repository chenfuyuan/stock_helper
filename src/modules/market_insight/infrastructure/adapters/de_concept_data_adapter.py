"""
Data Engineering 概念数据适配器
将 data_engineering 的概念数据转换为 market_insight 领域层 DTO
"""

from typing import List

from src.modules.data_engineering.container import DataEngineeringContainer
from src.modules.market_insight.domain.dtos.insight_dtos import (
    ConceptStockDTO,
    ConceptWithStocksDTO,
)
from src.modules.market_insight.domain.ports.concept_data_port import IConceptDataPort


class DeConceptDataAdapter(IConceptDataPort):
    """Data Engineering 概念数据适配器"""

    def __init__(self, de_container: DataEngineeringContainer):
        self._concept_repo = de_container.get_concept_repository()

    async def get_all_concepts_with_stocks(self) -> List[ConceptWithStocksDTO]:
        """
        获取所有概念板块及其成分股列表
        :return: 概念及成分股 DTO 列表
        """
        de_concepts = await self._concept_repo.get_all_concepts_with_stocks()

        return [
            ConceptWithStocksDTO(
                code=c.code,
                name=c.name,
                stocks=[
                    ConceptStockDTO(
                        third_code=s.third_code,
                        stock_name=s.stock_name,
                    )
                    for s in c.stocks
                ],
            )
            for c in de_concepts
        ]
