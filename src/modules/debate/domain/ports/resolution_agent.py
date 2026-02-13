"""
Resolution Agent Port。

Domain 层仅定义接口，由 Infrastructure 的 ResolutionAgentAdapter 实现。
"""
from abc import ABC, abstractmethod

from src.modules.debate.domain.dtos.bull_bear_argument import BearArgument, BullArgument
from src.modules.debate.domain.dtos.resolution_result import ResolutionResult


class IResolutionAgentPort(ABC):
    """冲突消解 Agent 抽象接口。"""

    @abstractmethod
    async def resolve(
        self,
        symbol: str,
        bull: BullArgument,
        bear: BearArgument,
    ) -> ResolutionResult:
        """基于多空论证进行交叉质疑与冲突消解，返回裁决结果。"""
        raise NotImplementedError
