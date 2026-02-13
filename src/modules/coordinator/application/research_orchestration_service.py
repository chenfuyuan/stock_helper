"""
ResearchOrchestrationService：薄编排服务，校验入参后委托 IResearchOrchestrationPort 执行。
"""
from src.modules.coordinator.domain.dtos.research_dtos import ResearchRequest, ResearchResult
from src.modules.coordinator.domain.exceptions import AllExpertsFailedError
from src.modules.coordinator.domain.model.enums import ExpertType
from src.modules.coordinator.domain.ports.research_orchestration import IResearchOrchestrationPort
from src.shared.domain.exceptions import BadRequestException


class ResearchOrchestrationService:
    """
    研究编排应用服务。

    职责：校验 symbol、experts，构建 ResearchRequest，调用 Port，根据 overall_status 返回或抛异常。
    """

    def __init__(self, orchestration_port: IResearchOrchestrationPort) -> None:
        self._orchestration_port = orchestration_port

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
            raise AllExpertsFailedError(
                message="全部专家执行失败，请检查数据或稍后重试"
            )

        return result
