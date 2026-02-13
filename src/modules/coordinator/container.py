"""
Coordinator 模块 Composition Root。

组装 ResearchGatewayAdapter → LangGraphResearchOrchestrator → ResearchOrchestrationService。
"""
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.coordinator.application.research_orchestration_service import (
    ResearchOrchestrationService,
)
from src.modules.coordinator.infrastructure.adapters.research_gateway_adapter import (
    ResearchGatewayAdapter,
)
from src.modules.coordinator.infrastructure.orchestration.langgraph_orchestrator import (
    LangGraphResearchOrchestrator,
)
from src.shared.infrastructure.db.session import AsyncSessionLocal


class CoordinatorContainer:
    """Coordinator 模块的依赖组装容器。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def research_orchestration_service(self) -> ResearchOrchestrationService:
        """
        组装研究编排服务：Gateway Adapter → LangGraph 编排器 → Application Service。

        Gateway 使用 AsyncSessionLocal 为每次专家调用创建独立会话，避免 LangGraph
        并行执行时多专家共享同一会话导致的 SQLAlchemy 并发错误。
        """
        gateway = ResearchGatewayAdapter(AsyncSessionLocal)
        orchestrator = LangGraphResearchOrchestrator(gateway)
        return ResearchOrchestrationService(orchestrator)
