"""
Bear Advocate Agent Port。

Domain 层仅定义接口，由 Infrastructure 的 BearAdvocateAgentAdapter 实现。
"""

from abc import ABC, abstractmethod

from src.modules.debate.domain.dtos.bull_bear_argument import BearArgument
from src.modules.debate.domain.dtos.debate_input import DebateInput


class IBearAdvocateAgentPort(ABC):
    """空头论证 Agent 抽象接口。"""

    @abstractmethod
    async def advocate(self, input_data: DebateInput) -> BearArgument:
        """基于辩论输入生成空头论证。"""
        raise NotImplementedError
