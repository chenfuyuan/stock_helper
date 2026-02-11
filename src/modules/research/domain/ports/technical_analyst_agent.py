"""
技术分析 Agent 的 Port。
入参为标的、分析日期与指标快照，出参为包含解析结果与原始 input/output 的 Agent 结果。
实现层负责加载/填充 Prompt、调用 LLM、解析结果；Application 不直接依赖 LLMPort 或 prompt 加载。
"""
from abc import ABC, abstractmethod

from src.modules.research.domain.dtos import TechnicalAnalysisAgentResult
from src.modules.research.domain.indicators_snapshot import TechnicalIndicatorsSnapshot


class ITechnicalAnalystAgentPort(ABC):
    """根据指标快照与上下文生成技术分析结果（内部完成 Prompt 加载、LLM 调用与解析）。"""

    @abstractmethod
    async def analyze(
        self,
        ticker: str,
        analysis_date: str,
        snapshot: TechnicalIndicatorsSnapshot,
    ) -> TechnicalAnalysisAgentResult:
        raise NotImplementedError
