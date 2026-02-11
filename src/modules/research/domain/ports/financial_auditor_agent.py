"""
财务审计 Agent 的 Port。
入参为标的与财务快照，出参为包含解析结果与原始 input/output 的 Agent 结果。
实现层负责加载/填充 Prompt、调用 LLM、解析结果；Application 不直接依赖 LLMPort 或 prompt 加载。
"""
from abc import ABC, abstractmethod

from src.modules.research.domain.financial_dtos import FinancialAuditAgentResult
from src.modules.research.domain.ports.dto_financial_inputs import FinancialSnapshotDTO


class IFinancialAuditorAgentPort(ABC):
    """根据财务快照与上下文生成财务审计结果（内部完成 Prompt 加载、LLM 调用与解析）。"""

    @abstractmethod
    async def audit(
        self,
        symbol: str,
        snapshot: FinancialSnapshotDTO,
    ) -> FinancialAuditAgentResult:
        raise NotImplementedError
