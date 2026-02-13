"""
LangGraph 研究编排图构建。

包含：通用专家节点工厂、5 个专家节点、Send 路由函数、聚合节点、图编译。
"""
import logging
from collections.abc import Callable
from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from src.modules.coordinator.domain.model.enums import ExpertType
from src.modules.coordinator.domain.ports.research_expert_gateway import IResearchExpertGateway
from src.modules.coordinator.infrastructure.orchestration.graph_state import ResearchGraphState

logger = logging.getLogger(__name__)

# 专家类型到图节点名的映射
EXPERT_NODE_NAMES = {
    ExpertType.TECHNICAL_ANALYST: "technical_analyst_node",
    ExpertType.FINANCIAL_AUDITOR: "financial_auditor_node",
    ExpertType.VALUATION_MODELER: "valuation_modeler_node",
    ExpertType.MACRO_INTELLIGENCE: "macro_intelligence_node",
    ExpertType.CATALYST_DETECTIVE: "catalyst_detective_node",
}


def create_expert_node(
    expert_type: ExpertType,
    gateway: IResearchExpertGateway,
) -> Callable[[ResearchGraphState], dict[str, Any]]:
    """
    专家节点工厂：为指定专家类型生成图节点函数。

    成功时写入 results[expert_type.value]，失败时写入 errors[expert_type.value]。
    """
    node_name = EXPERT_NODE_NAMES[expert_type]

    async def expert_node(state: ResearchGraphState) -> dict[str, Any]:
        try:
            options = state.get("options") or {}
            expert_opts = options.get(expert_type.value, {})
            result = await gateway.run_expert(
                expert_type=expert_type,
                symbol=state["symbol"],
                options=expert_opts,
            )
            return {"results": {expert_type.value: result}}
        except Exception as e:
            logger.warning("专家 %s 执行失败: %s", expert_type.value, e)
            return {"errors": {expert_type.value: str(e)}}

    expert_node.__name__ = node_name
    return expert_node


def route_to_experts(state: ResearchGraphState) -> list[Send]:
    """
    路由函数：读取 selected_experts，为每个选中的专家返回 Send(node_name, state)。

    用于 add_conditional_edges(START, route_to_experts)，实现按需并行 fan-out。
    """
    selected = state.get("selected_experts") or []
    sends: list[Send] = []
    for expert_value in selected:
        expert_type = ExpertType(expert_value)
        node_name = EXPERT_NODE_NAMES[expert_type]
        sends.append(Send(node_name, state))
    return sends


def create_aggregator_node() -> Callable[[ResearchGraphState], dict[str, Any]]:
    """聚合节点：根据 results 和 errors 设置 overall_status。"""

    def aggregator_node(state: ResearchGraphState) -> dict[str, Any]:
        results = state.get("results") or {}
        errors = state.get("errors") or {}

        if not results:
            overall_status = "failed"
        elif not errors:
            overall_status = "completed"
        else:
            overall_status = "partial"

        return {"overall_status": overall_status}

    return aggregator_node


def build_research_graph(
    gateway: IResearchExpertGateway,
) -> Any:
    """
    构建并编译研究编排图。

    Returns:
        CompiledGraph: 可 invoke 的编译后图
    """
    builder = StateGraph(ResearchGraphState)

    # 注册 5 个专家节点
    for expert_type in ExpertType:
        node_name = EXPERT_NODE_NAMES[expert_type]
        node_fn = create_expert_node(expert_type, gateway)
        builder.add_node(node_name, node_fn)

    # 聚合节点
    builder.add_node("aggregator_node", create_aggregator_node())

    # START -> 路由函数（返回 Send 列表，动态 fan-out 到选中的专家节点）
    builder.add_conditional_edges(START, route_to_experts)

    # 各专家节点 -> 聚合节点
    for node_name in EXPERT_NODE_NAMES.values():
        builder.add_edge(node_name, "aggregator_node")

    # 聚合节点 -> END
    builder.add_edge("aggregator_node", END)

    return builder.compile()
