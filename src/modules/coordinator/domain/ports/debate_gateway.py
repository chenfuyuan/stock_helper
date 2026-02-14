"""
IDebateGateway：Coordinator 调用 Debate 模块的 Port。

仅定义接口签名，由 Infrastructure 的 DebateGatewayAdapter 实现。
"""

from abc import ABC, abstractmethod
from typing import Any


class IDebateGateway(ABC):
    """辩论网关抽象接口。"""

    @abstractmethod
    async def run_debate(
        self, symbol: str, expert_results: dict[str, Any]
    ) -> dict[str, Any]:
        """
        执行辩论，返回辩论结果的 dict 序列化。

        Args:
            symbol: 标的代码
            expert_results: 按专家名分组的成功专家结果（与 ResearchGraphState.results 结构一致）

        Returns:
            辩论结果 dict（如 DebateOutcomeDTO.model_dump()）
        """
        raise NotImplementedError
