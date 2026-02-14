"""
Coordinator 模块 Composition Root。

组装 ResearchGatewayAdapter、DebateGatewayAdapter、JudgeGatewayAdapter
→ LangGraphResearchOrchestrator → ResearchOrchestrationService。
并注册 IResearchSessionRepository → PgResearchSessionRepository，注入到编排器以支持执行追踪。
"""

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.coordinator.application.research_orchestration_service import (
    ResearchOrchestrationService,
)
from src.modules.coordinator.infrastructure.adapters.debate_gateway_adapter import (
    DebateGatewayAdapter,
)
from src.modules.coordinator.infrastructure.adapters.judge_gateway_adapter import (
    JudgeGatewayAdapter,
)
from src.modules.coordinator.infrastructure.adapters.research_gateway_adapter import (
    ResearchGatewayAdapter,
)
from src.modules.coordinator.infrastructure.orchestration.langgraph_orchestrator import (
    LangGraphResearchOrchestrator,
)
from src.modules.coordinator.infrastructure.persistence.research_session_repository import (
    PgResearchSessionRepository,
)
from src.shared.infrastructure.db.session import AsyncSessionLocal


class CoordinatorContainer:
    """Coordinator 模块的依赖组装容器。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def research_orchestration_service(self) -> ResearchOrchestrationService:
        """
        组装研究编排服务：Gateway Adapters → LangGraph 编排器 → Application Service。

        Research Gateway 使用 AsyncSessionLocal 为每次专家调用创建独立会话；
        Debate / Judge Gateway 传入编排器，当 skip_debate=False 时执行辩论与裁决节点。
        session_repo 用于持久化 ResearchSession 与 NodeExecution，并设置 ExecutionContext。
        """
        gateway = ResearchGatewayAdapter(AsyncSessionLocal)
        debate_gateway = DebateGatewayAdapter(AsyncSessionLocal)
        judge_gateway = JudgeGatewayAdapter(AsyncSessionLocal)
        session_repo = PgResearchSessionRepository(self._session)
        orchestrator = LangGraphResearchOrchestrator(
            gateway,
            debate_gateway=debate_gateway,
            judge_gateway=judge_gateway,
            session_repo=session_repo,
        )
        return ResearchOrchestrationService(orchestrator, session_repo=session_repo)
