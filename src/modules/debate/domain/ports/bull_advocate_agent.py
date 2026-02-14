"""
Bull Advocate Agent Port。

Domain 层仅定义接口，由 Infrastructure 的 BullAdvocateAgentAdapter 实现。
"""

from abc import ABC, abstractmethod

from src.modules.debate.domain.dtos.bull_bear_argument import BullArgument
from src.modules.debate.domain.dtos.debate_input import DebateInput


class IBullAdvocateAgentPort(ABC):
    """多头论证 Agent 抽象接口。"""

    @abstractmethod
    async def advocate(self, input_data: DebateInput) -> BullArgument:
        """基于辩论输入生成多头论证。"""
        raise NotImplementedError
