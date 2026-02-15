"""
概念数据查询接口
用于从 data_engineering 获取概念板块与成分股映射
"""

from abc import ABC, abstractmethod
from typing import List

from src.modules.market_insight.domain.dtos.insight_dtos import ConceptWithStocksDTO


class IConceptDataPort(ABC):
    """概念数据查询接口"""
    
    @abstractmethod
    async def get_all_concepts_with_stocks(self) -> List[ConceptWithStocksDTO]:
        """
        获取所有概念板块及其成分股列表
        :return: 概念及成分股 DTO 列表
        """
        pass
