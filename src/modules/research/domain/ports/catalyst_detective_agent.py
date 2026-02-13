from abc import ABC, abstractmethod

from src.modules.research.domain.dtos.catalyst_context import CatalystContextDTO
from src.modules.research.domain.dtos.catalyst_dtos import CatalystDetectiveAgentResult


class ICatalystDetectiveAgentPort(ABC):
    @abstractmethod
    def analyze(
        self, symbol: str, catalyst_context: CatalystContextDTO
    ) -> CatalystDetectiveAgentResult:
        """
        调用 LLM 对催化剂上下文进行分析，返回结构化结果
        """
        pass
