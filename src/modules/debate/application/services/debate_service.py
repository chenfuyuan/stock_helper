"""
DebateService：编排三阶段辩论流程（Bull/Bear 并行 → Resolution 串行），返回 DebateOutcomeDTO。
"""
import asyncio

from src.modules.debate.application.dtos.debate_outcome_dto import (
    BearCaseDTO,
    BullCaseDTO,
    DebateOutcomeDTO,
)
from src.modules.debate.domain.dtos.debate_input import DebateInput
from src.modules.debate.domain.ports.bear_advocate_agent import IBearAdvocateAgentPort
from src.modules.debate.domain.ports.bull_advocate_agent import IBullAdvocateAgentPort
from src.modules.debate.domain.ports.resolution_agent import IResolutionAgentPort


class DebateService:
    """
    辩论应用服务。

    入参校验、Bull/Bear 并行执行（asyncio.gather）、Resolution 串行执行、
    将 ResolutionResult 组装为 DebateOutcomeDTO 返回。
    """

    def __init__(
        self,
        bull_agent: IBullAdvocateAgentPort,
        bear_agent: IBearAdvocateAgentPort,
        resolution_agent: IResolutionAgentPort,
    ) -> None:
        self._bull_agent = bull_agent
        self._bear_agent = bear_agent
        self._resolution_agent = resolution_agent

    async def run(self, debate_input: DebateInput) -> DebateOutcomeDTO:
        """
        执行三阶段辩论：Bull 与 Bear 并行，Resolution 串行。
        任一 Agent 抛异常时向上传播，由调用方处理。
        """
        bull, bear = await asyncio.gather(
            self._bull_agent.advocate(debate_input),
            self._bear_agent.advocate(debate_input),
        )
        resolution = await self._resolution_agent.resolve(
            symbol=debate_input.symbol,
            bull=bull,
            bear=bear,
        )
        return DebateOutcomeDTO(
            symbol=debate_input.symbol,
            direction=resolution.direction,
            confidence=resolution.confidence,
            bull_case=BullCaseDTO(
                core_thesis=bull.core_thesis,
                supporting_arguments=bull.supporting_arguments,
                acknowledged_risks=bull.acknowledged_risks,
            ),
            bear_case=BearCaseDTO(
                core_thesis=bear.core_thesis,
                supporting_arguments=bear.supporting_arguments,
                acknowledged_strengths=bear.acknowledged_strengths,
            ),
            risk_matrix=resolution.risk_matrix,
            key_disagreements=resolution.key_disagreements,
            conflict_resolution=resolution.conflict_resolution,
        )
