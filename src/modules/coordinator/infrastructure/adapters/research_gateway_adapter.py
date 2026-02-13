"""
ResearchGatewayAdapter：实现 IResearchExpertGateway，通过 ResearchContainer 调用 Research 专家服务。

负责将 CatalystDetectiveAgentResult 归一化为 dict，以及专家参数的解析与透传。

注意：LangGraph 并行执行各专家节点，每个节点会同时调用 run_expert。
SQLAlchemy AsyncSession 不支持并发操作，因此每次 run_expert 必须使用独立会话。
"""
from datetime import date
from typing import Any

from src.modules.coordinator.domain.model.enums import ExpertType
from src.modules.coordinator.domain.ports.research_expert_gateway import IResearchExpertGateway
from src.modules.research.container import ResearchContainer


class ResearchGatewayAdapter(IResearchExpertGateway):
    """
    通过 ResearchContainer 调度到对应 Research Application Service 的 Gateway 实现。

    每次 run_expert 使用独立 AsyncSession，避免 LangGraph 并行节点共享同一会话导致
    "concurrent operations are not permitted" 错误。
    """

    def __init__(self, session_factory: Any) -> None:
        """
        Args:
            session_factory: 异步会话工厂，如 AsyncSessionLocal。
                每次调用 run_expert 时创建新会话，保证并行专家互不干扰。
        """
        self._session_factory = session_factory

    def _normalize_catalyst_result(self, agent_result: Any) -> dict[str, Any]:
        """
        将 CatalystDetectiveService 返回的 CatalystDetectiveAgentResult 归一化为 dict[str, Any]。

        使 Coordinator 拿到的所有专家结果类型一致，便于图节点统一处理。
        """
        return {
            "result": agent_result.result.model_dump(),
            "raw_llm_output": agent_result.raw_llm_output,
            "user_prompt": agent_result.user_prompt,
            "catalyst_context": agent_result.catalyst_context.model_dump(),
        }

    def _parse_analysis_date(self, value: Any) -> date:
        """将 options 中的 analysis_date（str 或 date）解析为 date。"""
        if value is None:
            return date.today()
        if isinstance(value, date):
            return value
        if isinstance(value, str):
            return date.fromisoformat(value)
        raise ValueError(f"analysis_date 须为 ISO 日期字符串或 date，收到: {type(value)}")

    async def run_expert(
        self,
        expert_type: ExpertType,
        symbol: str,
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        根据专家类型调度到对应的 Research Application Service，返回归一化后的 dict。

        每次调用使用独立 AsyncSession，满足 LangGraph 并行执行的会话隔离要求。
        """
        opts = options or {}

        async with self._session_factory() as session:
            research = ResearchContainer(session)
            match expert_type:
                case ExpertType.TECHNICAL_ANALYST:
                    expert_opts = opts.get("technical_analyst", {})
                    analysis_date = self._parse_analysis_date(
                        expert_opts.get("analysis_date", date.today())
                    )
                    svc = research.technical_analyst_service()
                    return await svc.run(ticker=symbol, analysis_date=analysis_date)

                case ExpertType.FINANCIAL_AUDITOR:
                    expert_opts = opts.get("financial_auditor", {})
                    limit = expert_opts.get("limit", 5)
                    svc = research.financial_auditor_service()
                    return await svc.run(symbol=symbol, limit=int(limit))

                case ExpertType.VALUATION_MODELER:
                    svc = research.valuation_modeler_service()
                    return await svc.run(symbol=symbol)

                case ExpertType.MACRO_INTELLIGENCE:
                    svc = research.macro_intelligence_service()
                    return await svc.run(symbol=symbol)

                case ExpertType.CATALYST_DETECTIVE:
                    svc = research.catalyst_detective_service()
                    agent_result = await svc.run(symbol=symbol)
                    return self._normalize_catalyst_result(agent_result)
