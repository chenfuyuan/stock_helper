"""
概念关系分析器 Port 接口。

定义基于 LLM 的概念关系推荐能力抽象。
"""

from abc import ABC, abstractmethod

from ..dtos.concept_relation_analyzer_dtos import ConceptForAnalysis, SuggestedRelation


class IConceptRelationAnalyzer(ABC):
    """
    概念关系分析器接口。
    
    利用 LLM 分析给定概念集合，推荐概念间的语义关系（上下游、竞争等）。
    """

    @abstractmethod
    async def analyze_relations(
        self, concepts: list[ConceptForAnalysis]
    ) -> list[SuggestedRelation]:
        """
        分析给定概念列表，推荐概念间关系。
        
        基于 LLM 的产业链分析能力，识别概念间的上下游、竞争、组成等关系，
        并给出置信度和推理依据。
        
        Args:
            concepts: 待分析的概念列表（code + name）
        
        Returns:
            推荐的关系列表（含关系类型、置信度、推理依据）
        
        注意：
        - 返回的关系不包含重复（source + target + type 组合唯一）
        - 如果 LLM 输出格式异常，降级返回空列表并记录日志
        - 所有推荐关系默认为 PENDING 状态，需人工确认
        """
        pass
