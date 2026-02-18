from abc import ABC, abstractmethod

from src.modules.data_engineering.domain.dtos.concept_dtos import ConceptWithStocksDTO
from src.modules.data_engineering.domain.model.concept import Concept, ConceptStock


class IConceptRepository(ABC):
    """
    概念数据仓储 Port
    定义概念板块数据的持久化能力
    """

    @abstractmethod
    async def upsert_concept(self, concept: Concept) -> int:
        """
        单个概念 UPSERT（by code）
        
        Args:
            concept: 概念对象
            
        Returns:
            int: 影响的行数
        """

    @abstractmethod
    async def upsert_concept_with_stocks(self, concept: Concept, stocks: list[ConceptStock]) -> int:
        """
        在一个事务中完成概念 UPSERT 和成份股替换
        
        Args:
            concept: 概念对象
            stocks: 成份股列表
            
        Returns:
            int: 总影响的行数（概念1行 + 成份股行数）
        """

    @abstractmethod
    async def replace_concept_stocks(self, concept_code: str, stocks: list[ConceptStock]) -> int:
        """
        替换指定概念的成份股映射（先清后建）
        
        Args:
            concept_code: 概念板块代码
            stocks: 成份股列表
            
        Returns:
            int: 插入的行数
        """

    @abstractmethod
    async def upsert_concepts(self, concepts: list[Concept]) -> int:
        """
        批量 UPSERT 概念记录（by code）
        
        Args:
            concepts: 概念列表
            
        Returns:
            int: 影响的行数
        """

    @abstractmethod
    async def replace_all_concept_stocks(self, mappings: list[ConceptStock]) -> int:
        """
        全量替换 concept_stock 表（先清后建）
        
        Args:
            mappings: 概念-股票映射列表
            
        Returns:
            int: 插入的行数
        """

    @abstractmethod
    async def get_all_concepts(self) -> list[Concept]:
        """
        查询所有概念记录
        
        Returns:
            list[Concept]: 概念列表
        """

    @abstractmethod
    async def get_concept_stocks(self, concept_code: str) -> list[ConceptStock]:
        """
        查询指定概念的成份股
        
        Args:
            concept_code: 概念板块代码
            
        Returns:
            list[ConceptStock]: 成份股列表
        """

    @abstractmethod
    async def get_all_concepts_with_stocks(self) -> list[ConceptWithStocksDTO]:
        """
        查询所有概念及其成份股（聚合查询，供 KC 适配器使用）
        
        Returns:
            list[ConceptWithStocksDTO]: 概念及成份股聚合列表
        """
