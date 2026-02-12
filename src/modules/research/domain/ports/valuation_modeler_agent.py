"""
估值建模 Agent 的 Port。
Domain 层定义「调用估值 Agent」契约，具体实现（Prompt 加载/填充、LLM 调用、解析）在 Infrastructure 层。
"""
from abc import ABC, abstractmethod

from src.modules.research.domain.dtos.valuation_dtos import ValuationModelAgentResult
from src.modules.research.domain.dtos.valuation_snapshot import ValuationSnapshotDTO


class IValuationModelerAgentPort(ABC):
    """
    调用估值建模 Agent，返回估值分析结果（解析后的 DTO + 原始 input/output）。
    """

    @abstractmethod
    async def analyze(
        self,
        symbol: str,
        snapshot: ValuationSnapshotDTO,
    ) -> ValuationModelAgentResult:
        """
        基于估值快照进行估值分析。
        加载 System Prompt 与 User Prompt 模板，填充占位符，调用 LLM，解析结果。
        解析失败时抛出 LLMOutputParseError。
        """
        raise NotImplementedError
