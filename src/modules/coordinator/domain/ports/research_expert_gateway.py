"""
Research 专家调用 Gateway Port。

Coordinator 通过此 Port 调用 Research 模块的专家，Infrastructure 层由 ResearchGatewayAdapter 实现，
内部通过 ResearchContainer 获取对应的 Application Service 并调用。
"""
from abc import ABC, abstractmethod
from typing import Any

from src.modules.coordinator.domain.model.enums import ExpertType


class IResearchExpertGateway(ABC):
    """调用指定类型 Research 专家的抽象接口。"""

    @abstractmethod
    async def run_expert(
        self,
        expert_type: ExpertType,
        symbol: str,
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        调用指定类型的 Research 专家，返回该专家的分析结果。

        Args:
            expert_type: 专家类型
            symbol: 股票代码
            options: 可选参数，如 technical_analyst 的 analysis_date、financial_auditor 的 limit

        Returns:
            专家的分析结果字典，统一为 dict[str, Any]
        """
        ...
