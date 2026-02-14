"""
ResearchOrchestrationService：薄编排服务，校验入参后委托 IResearchOrchestrationPort 执行。
"""

from typing import Any
from uuid import UUID

from src.modules.coordinator.domain.dtos.research_dtos import (
    ResearchRequest,
    ResearchResult,
)
from src.modules.coordinator.domain.exceptions import (
    AllExpertsFailedError,
    SessionNotFoundError,
    SessionNotRetryableError,
)
from src.modules.coordinator.domain.model.enums import ExpertType
from src.modules.coordinator.domain.ports.research_orchestration import (
    IResearchOrchestrationPort,
)
from src.modules.coordinator.domain.ports.research_session_repository import (
    IResearchSessionRepository,
)
from src.shared.domain.exceptions import BadRequestException


class ResearchOrchestrationService:
    """
    研究编排应用服务。

    职责：校验 symbol、experts，构建 ResearchRequest，调用 Port，根据 overall_status 返回或抛异常。
    """

    def __init__(
        self,
        orchestration_port: IResearchOrchestrationPort,
        session_repo: IResearchSessionRepository | None = None,
    ) -> None:
        self._orchestration_port = orchestration_port
        self._session_repo = session_repo

    async def execute(
        self,
        symbol: str,
        experts: list[str],
        options: dict[str, dict] | None = None,
        skip_debate: bool = False,
    ) -> ResearchResult:
        """
        执行研究编排。

        Args:
            symbol: 股票代码
            experts: 专家类型列表（ExpertType 的 value 字符串）
            options: 各专家可选参数

        Returns:
            研究编排结果

        Raises:
            BadRequestException: symbol 为空、experts 为空或含非法类型
            AllExpertsFailedError: 全部专家执行失败
        """
        # 1. 校验 symbol
        if not symbol or not str(symbol).strip():
            raise BadRequestException(message="symbol 为必填")

        # 2. 校验 experts 非空且合法
        if not experts:
            raise BadRequestException(message="experts 为必填，至少指定一个专家")

        valid_values = {e.value for e in ExpertType}
        expert_types: list[ExpertType] = []
        for ex in experts:
            if ex not in valid_values:
                raise BadRequestException(
                    message=f"experts 含非法值: {ex}，合法值为 {sorted(valid_values)}"
                )
            expert_types.append(ExpertType(ex))

        # 3. 构建 ResearchRequest 并调用 Port
        request = ResearchRequest(
            symbol=symbol.strip(),
            experts=expert_types,
            options=options or {},
            skip_debate=skip_debate,
        )
        result = await self._orchestration_port.run(request)

        # 4. 全部失败时抛出领域异常
        if result.overall_status == "failed":
            raise AllExpertsFailedError(message="全部专家执行失败，请检查数据或稍后重试")

        return result

    async def retry(
        self,
        session_id: UUID,
        skip_debate: bool = False,
    ) -> ResearchResult:
        """
        对已有 session 中失败的专家发起重试，复用成功专家的结果。

        Args:
            session_id: 源 session ID
            skip_debate: 是否跳过辩论和裁决阶段

        Returns:
            重试后的完整研究结果（含复用的成功结果 + 重新执行的失败专家结果）

        Raises:
            SessionNotFoundError: session 不存在
            SessionNotRetryableError: session 状态为 completed（无需重试）或 running（执行中）
            AllExpertsFailedError: 重试后全部专家仍失败
        """
        if self._session_repo is None:
            raise SessionNotFoundError(message="未启用持久化，无法进行重试")

        # 1. 查询源 session
        source_session = await self._session_repo.get_session_by_id(session_id)
        if source_session is None:
            raise SessionNotFoundError(message=f"研究会话 {session_id} 不存在")

        # 2. 校验状态
        if source_session.status == "completed":
            raise SessionNotRetryableError(
                message="该研究会话已完成，无需重试",
                status_code=400,
            )
        if source_session.status == "running":
            raise SessionNotRetryableError(
                message="该研究会话正在执行中，请等待完成后再重试",
                status_code=409,
            )

        # 3. 查询 NodeExecution 记录，分离成功/失败的专家
        node_executions = await self._session_repo.get_node_executions_by_session(session_id)

        # 仅处理专家类型节点（排除 debate、judge）
        expert_values = {e.value for e in ExpertType}
        success_results: dict[str, Any] = {}
        failed_experts: list[ExpertType] = []

        for ne in node_executions:
            if ne.node_type not in expert_values:
                continue
            if ne.status == "success" and ne.result_data is not None:
                success_results[ne.node_type] = ne.result_data
            elif ne.status == "failed":
                failed_experts.append(ExpertType(ne.node_type))

        # 没有失败专家时（理论上不应到这里，但防御性处理）
        if not failed_experts:
            raise SessionNotRetryableError(
                message="该研究会话没有失败的专家节点，无需重试",
                status_code=400,
            )

        # 4. 构建重试请求
        request = ResearchRequest(
            symbol=source_session.symbol,
            experts=failed_experts,
            options=source_session.options or {},
            skip_debate=skip_debate,
            pre_populated_results=success_results if success_results else None,
            parent_session_id=session_id,
            retry_count=source_session.retry_count + 1,
        )

        # 5. 委托编排执行
        result = await self._orchestration_port.run(request)

        # 6. 全部失败时抛出领域异常
        if result.overall_status == "failed":
            raise AllExpertsFailedError(message="重试后全部专家仍执行失败，请检查数据或稍后重试")

        return result
