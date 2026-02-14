from abc import ABC, abstractmethod

from src.modules.data_engineering.domain.dtos.concept_dtos import (
    ConceptConstituentDTO,
    ConceptInfoDTO,
)


class IConceptDataProvider(ABC):
    """
    概念数据提供者 Port
    定义从外部数据源获取概念板块数据的能力
    """

    @abstractmethod
    async def fetch_concept_list(self) -> list[ConceptInfoDTO]:
        """
        获取所有概念板块列表
        
        Returns:
            list[ConceptInfoDTO]: 概念板块列表，包含 code 和 name
        """

    @abstractmethod
    async def fetch_concept_constituents(self, symbol: str) -> list[ConceptConstituentDTO]:
        """
        获取指定概念板块的成份股列表
        
        Args:
            symbol: 概念板块名称（如 "低空经济"）
            
        Returns:
            list[ConceptConstituentDTO]: 成份股列表，股票代码已转换为系统标准格式
        """
