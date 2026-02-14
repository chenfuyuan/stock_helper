"""
LangGraphResearchOrchestrator：实现 IResearchOrchestrationPort，基于 LangGraph 执行研究编排。
"""
from datetime import datetime
from typing import Any
from uuid import uuid4

from src.shared.infrastructure.execution_context import current_execution_ctx, ExecutionContext
from src.modules.coordinator.domain.dtos.research_dtos import (
    ExpertResultItem,
    ResearchRequest,
    ResearchResult,
)
from src.modules.coordinator.domain.model.enums import ExpertType
from src.modules.coordinator.domain.model.research_session import ResearchSession
from src.modules.coordinator.domain.ports.research_expert_gateway import IResearchExpertGateway
from src.modules.coordinator.domain.ports.research_orchestration import IResearchOrchestrationPort
from src.modules.coordinator.domain.ports.research_session_repository import IResearchSessionRepository
from src.modules.coordinator.infrastructure.orchestration.graph_builder import (
    build_research_graph,
)


class LangGraphResearchOrchestrator(IResearchOrchestrationPort):
    """
    基于 LangGraph 的研究编排器。

    接收 IResearchExpertGateway，可选 IDebateGateway、IJudgeGateway、IResearchSessionRepository；
    skip_debate 时辩论与裁决均跳过；在 run() 中创建 ResearchSession、设置 ExecutionContext、
    执行图、更新 session 状态并重置 context，最后将 state 转为 ResearchResult。
    """

    def __init__(
        self,
        gateway: IResearchExpertGateway,
        debate_gateway: Any = None,
        judge_gateway: Any = None,
        session_repo: IResearchSessionRepository | None = None,
    ) -> None:
        self._gateway = gateway
        self._debate_gateway = debate_gateway
        self._judge_gateway = judge_gateway
        self._session_repo = session_repo

    async def run(self, request: ResearchRequest) -> ResearchResult:
        """执行研究编排，返回汇总结果。"""
        started_at = datetime.utcnow()
        session: ResearchSession | None = None
        token = None

        if self._session_repo is not None:
            session = ResearchSession(
                id=uuid4(),
                symbol=request.symbol,
                status="running",
                selected_experts=[e.value for e in request.experts],
                options=request.options,
                trigger_source="api",
                created_at=started_at,
                retry_count=request.retry_count,
                parent_session_id=request.parent_session_id,
            )
            await self._session_repo.save_session(session)
            token = current_execution_ctx.set(ExecutionContext(session_id=str(session.id)))

        try:
            debate_gw = None if request.skip_debate else self._debate_gateway
            judge_gw = None if request.skip_debate else self._judge_gateway
            graph = build_research_graph(
                self._gateway,
                debate_gateway=debate_gw,
                judge_gateway=judge_gw,
                session_repo=self._session_repo,
            )

            initial_state = {
                "symbol": request.symbol,
                "selected_experts": [e.value for e in request.experts],
                "options": request.options,
                "results": request.pre_populated_results or {},
            }

            final_state = await graph.ainvoke(initial_state)

            results = final_state.get("results") or {}
            overall_status = final_state.get("overall_status") or "failed"

            expert_results: list[ExpertResultItem] = []

            # 重试时 pre_populated_results 中的专家不在 request.experts 中，
            # 需要将其加入 expert_results（标记为 success）
            pre_populated = request.pre_populated_results or {}
            for expert_value, data in pre_populated.items():
                expert_type = ExpertType(expert_value)
                expert_results.append(
                    ExpertResultItem(
                        expert_type=expert_type,
                        status="success",
                        data=data,
                        error=None,
                    )
                )

            # 所有请求的专家都应该成功，因为失败会抛异常停止流程
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
                    # 理论上不应该到这里，因为失败会抛异常
                    expert_results.append(
                        ExpertResultItem(
                            expert_type=expert_type,
                            status="failed",
                            data=None,
                            error="专家结果缺失",
                        )
                    )

            debate_outcome = final_state.get("debate_outcome")
            if debate_outcome == {}:
                debate_outcome = None

            verdict = final_state.get("verdict")
            if verdict == {}:
                verdict = None

            completed_at = datetime.utcnow()
            duration_ms = int((completed_at - started_at).total_seconds() * 1000)
            if session and self._session_repo is not None:
                if overall_status == "completed":
                    session.complete(completed_at, duration_ms)
                else:
                    session.fail(completed_at, duration_ms)
                await self._session_repo.update_session(session)

            return ResearchResult(
                symbol=request.symbol,
                overall_status=overall_status,
                expert_results=expert_results,
                debate_outcome=debate_outcome,
                verdict=verdict,
                session_id=str(session.id) if session else "",
                retry_count=request.retry_count,
            )
        finally:
            if token is not None:
                current_execution_ctx.reset(token)
