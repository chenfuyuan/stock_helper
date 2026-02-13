"""
LangGraphResearchOrchestrator：实现 IResearchOrchestrationPort，基于 LangGraph 执行研究编排。
"""
from src.modules.coordinator.domain.dtos.research_dtos import (
    ExpertResultItem,
    ResearchRequest,
    ResearchResult,
)
from src.modules.coordinator.domain.model.enums import ExpertType
from src.modules.coordinator.domain.ports.research_expert_gateway import IResearchExpertGateway
from src.modules.coordinator.domain.ports.research_orchestration import IResearchOrchestrationPort
from src.modules.coordinator.infrastructure.orchestration.graph_builder import (
    build_research_graph,
)


class LangGraphResearchOrchestrator(IResearchOrchestrationPort):
    """
    基于 LangGraph 的研究编排器。

    接收 IResearchExpertGateway，在 run() 中构建图、执行、将 state 转为 ResearchResult。
    """

    def __init__(self, gateway: IResearchExpertGateway) -> None:
        self._gateway = gateway

    async def run(self, request: ResearchRequest) -> ResearchResult:
        """执行研究编排，返回汇总结果。"""
        graph = build_research_graph(self._gateway)

        # 构建初始 state
        initial_state = {
            "symbol": request.symbol,
            "selected_experts": [e.value for e in request.experts],
            "options": request.options,
            "results": {},
            "errors": {},
        }

        # 执行图
        final_state = await graph.ainvoke(initial_state)

        # 转为 ResearchResult
        results = final_state.get("results") or {}
        errors = final_state.get("errors") or {}
        overall_status = final_state.get("overall_status") or "failed"

        expert_results: list[ExpertResultItem] = []
        for expert_type in request.experts:
            expert_value = expert_type.value
            if expert_value in results:
                expert_results.append(
                    ExpertResultItem(
                        expert_type=expert_type,
                        status="success",
                        data=results[expert_value],
                        error=None,
                    )
                )
            else:
                expert_results.append(
                    ExpertResultItem(
                        expert_type=expert_type,
                        status="failed",
                        data=None,
                        error=errors.get(expert_value, "未知错误"),
                    )
                )

        return ResearchResult(
            symbol=request.symbol,
            overall_status=overall_status,
            expert_results=expert_results,
        )
