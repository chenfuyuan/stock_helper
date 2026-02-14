"""
IJudgeGateway：Coordinator 调用 Judge 模块的 Port。

仅定义接口签名，由 Infrastructure 的 JudgeGatewayAdapter 实现。
"""

from abc import ABC, abstractmethod
from typing import Any


class IJudgeGateway(ABC):
    """裁决网关抽象接口。"""

    @abstractmethod
    async def run_verdict(self, symbol: str, debate_outcome: dict[str, Any]) -> dict[str, Any]:
        """
        执行裁决，返回裁决结果的 dict 序列化。

        Args:
            symbol: 标的代码
            debate_outcome: 辩论结果 dict（与 ResearchGraphState.debate_outcome 结构一致）

        Returns:
            裁决结果 dict（如 VerdictDTO.model_dump()）
        """
        raise NotImplementedError
