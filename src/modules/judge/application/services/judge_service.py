"""
Judge 应用服务：编排裁决流程。

接收 JudgeInput，调用 IJudgeVerdictAgentPort.judge()，组装 VerdictDTO 返回（从 JudgeInput 注入 symbol）。
"""
from src.modules.judge.application.dtos.verdict_dto import VerdictDTO
from src.modules.judge.domain.dtos.judge_input import JudgeInput
from src.modules.judge.domain.ports.judge_verdict_agent import IJudgeVerdictAgentPort


class JudgeService:
    """Judge 模块唯一 Application 入口：执行单次综合裁决。"""

    def __init__(self, verdict_agent: IJudgeVerdictAgentPort) -> None:
        self._verdict_agent = verdict_agent

    async def run(self, judge_input: JudgeInput) -> VerdictDTO:
        """
        执行裁决：调用 Agent Port 获得 VerdictResult，注入 symbol 后返回 VerdictDTO。
        若 Agent 抛异常，则异常向上传播，由调用方处理。
        """
        result = await self._verdict_agent.judge(judge_input)
        return VerdictDTO(
            symbol=judge_input.symbol,
            action=result.action,
            position_percent=result.position_percent,
            confidence=result.confidence,
            entry_strategy=result.entry_strategy,
            stop_loss=result.stop_loss,
            take_profit=result.take_profit,
            time_horizon=result.time_horizon,
            risk_warnings=result.risk_warnings,
            reasoning=result.reasoning,
        )
