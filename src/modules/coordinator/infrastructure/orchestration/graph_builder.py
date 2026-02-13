"""
LangGraph 研究编排图构建。

包含：通用专家节点工厂、5 个专家节点、Send 路由函数、聚合节点、debate 节点、图编译。
当提供 session_repo 时，专家节点、debate、judge 均用 persist_node_execution 包装以持久化节点执行。
"""
import logging
from collections.abc import Callable
from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from src.modules.coordinator.domain.model.enums import ExpertType
from src.modules.coordinator.domain.ports.research_expert_gateway import IResearchExpertGateway
from src.modules.coordinator.domain.ports.research_session_repository import IResearchSessionRepository
from src.modules.coordinator.infrastructure.orchestration.graph_state import ResearchGraphState
from src.modules.coordinator.infrastructure.orchestration.node_persistence_wrapper import persist_node_execution

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


def create_debate_node(debate_gateway: Any) -> Callable[[ResearchGraphState], dict[str, Any]]:
    """
    debate 节点工厂：读取 results/overall_status，全部失败时跳过辩论；
    否则调用 IDebateGateway.run_debate；异常时记录日志并降级（debate_outcome 为空 dict）。
    """

    async def debate_node(state: ResearchGraphState) -> dict[str, Any]:
        overall_status = state.get("overall_status") or "failed"
        results = state.get("results") or {}
        symbol = state.get("symbol") or ""

        if overall_status == "failed" or not results:
            return {"debate_outcome": {}}

        try:
            outcome = await debate_gateway.run_debate(symbol=symbol, expert_results=results)
            return {"debate_outcome": outcome}
        except Exception as e:
            logger.warning("辩论节点执行失败，降级为空结果: %s", e)
            return {"debate_outcome": {}}

    debate_node.__name__ = "debate_node"
    return debate_node


def create_judge_node(judge_gateway: Any) -> Callable[[ResearchGraphState], dict[str, Any]]:
    """
    judge 节点工厂：读取 debate_outcome，为空时跳过裁决；
    否则调用 IJudgeGateway.run_verdict；异常时记录日志并降级（verdict 为空 dict）。
    """

    async def judge_node(state: ResearchGraphState) -> dict[str, Any]:
        debate_outcome = state.get("debate_outcome") or {}
        symbol = state.get("symbol") or ""

        if not debate_outcome:
            return {"verdict": {}}

        try:
            verdict = await judge_gateway.run_verdict(symbol=symbol, debate_outcome=debate_outcome)
            return {"verdict": verdict}
        except Exception as e:
            logger.warning("裁决节点执行失败，降级为空结果: %s", e)
            return {"verdict": {}}

    judge_node.__name__ = "judge_node"
    return judge_node


def build_research_graph(
    gateway: IResearchExpertGateway,
    debate_gateway: Any = None,
    judge_gateway: Any = None,
    session_repo: IResearchSessionRepository | None = None,
) -> Any:
    """
    构建并编译研究编排图。

    - debate_gateway 和 judge_gateway 均不为 None：aggregator -> debate_node -> judge_node -> END
    - 仅 debate_gateway 不为 None：aggregator -> debate_node -> END
    - debate_gateway 为 None：aggregator -> END（不接入辩论与裁决）
    - session_repo 不为 None 时，专家节点、debate、judge 均用 persist_node_execution 包装以持久化节点执行。
    """
    builder = StateGraph(ResearchGraphState)

    def _wrap_if_persist(fn: Callable, node_type: str) -> Callable:
        if session_repo is not None:
            return persist_node_execution(fn, node_type, session_repo)
        return fn

    # 注册 5 个专家节点
    for expert_type in ExpertType:
        node_name = EXPERT_NODE_NAMES[expert_type]
        node_fn = create_expert_node(expert_type, gateway)
        node_fn = _wrap_if_persist(node_fn, expert_type.value)
        builder.add_node(node_name, node_fn)

    # 聚合节点
    builder.add_node("aggregator_node", create_aggregator_node())

    if debate_gateway is not None:
        debate_fn = create_debate_node(debate_gateway)
        debate_fn = _wrap_if_persist(debate_fn, "debate")
        builder.add_node("debate_node", debate_fn)
        builder.add_edge("aggregator_node", "debate_node")
        if judge_gateway is not None:
            judge_fn = create_judge_node(judge_gateway)
            judge_fn = _wrap_if_persist(judge_fn, "judge")
            builder.add_node("judge_node", judge_fn)
            builder.add_edge("debate_node", "judge_node")
            builder.add_edge("judge_node", END)
        else:
            builder.add_edge("debate_node", END)
    else:
        builder.add_edge("aggregator_node", END)

    # START -> 路由函数（返回 Send 列表，动态 fan-out 到选中的专家节点）
    builder.add_conditional_edges(START, route_to_experts)

    # 各专家节点 -> 聚合节点
    for node_name in EXPERT_NODE_NAMES.values():
        builder.add_edge(node_name, "aggregator_node")

    return builder.compile()
