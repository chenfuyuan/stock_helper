"""
研究编排图状态定义。

使用 TypedDict + Annotated reducer，使并行专家节点各自写入 results/errors 后自动合并。
"""

from typing import Any, Literal, TypedDict

from typing_extensions import Annotated

from src.modules.coordinator.infrastructure.orchestration.reducers import (
    merge_dicts,
)


class ResearchGraphState(TypedDict, total=False):
    """
    研究编排图状态。

    - symbol、selected_experts、options 为输入
    - results、errors 由各专家节点并行写入，通过 merge_dicts 合并
    - overall_status 由聚合节点设置
    """

    symbol: str
    selected_experts: list[str]
    options: dict[str, dict[str, Any]]
    results: Annotated[dict[str, Any], merge_dicts]
    errors: Annotated[dict[str, str], merge_dicts]
    overall_status: Literal["completed", "partial", "failed"]
    debate_outcome: dict[str, Any]  # 由 debate_node 写入
    verdict: dict[str, Any]  # 由 judge_node 写入
