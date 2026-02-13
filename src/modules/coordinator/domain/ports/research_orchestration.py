"""
研究编排 Port。

Application 层通过此 Port 委托编排执行，Infrastructure 层由 LangGraphResearchOrchestrator 实现。
"""
from abc import ABC, abstractmethod

from src.modules.coordinator.domain.dtos.research_dtos import (
    ResearchRequest,
    ResearchResult,
)


class IResearchOrchestrationPort(ABC):
    """研究编排抽象接口。"""

    @abstractmethod
    async def run(self, request: ResearchRequest) -> ResearchResult:
        """
        执行研究编排，返回汇总结果。

        Args:
            request: 研究请求（symbol、专家列表、可选参数）

        Returns:
            汇总后的研究结果（overall_status、各专家结果）
        """
        ...
