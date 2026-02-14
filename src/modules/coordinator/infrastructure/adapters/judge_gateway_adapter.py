"""
JudgeGatewayAdapter：实现 IJudgeGateway。

将 debate_outcome dict 转为 JudgeInput，调用 JudgeContainer → JudgeService，返回 dict。
"""

from typing import Any

from src.modules.coordinator.domain.ports.judge_gateway import IJudgeGateway
from src.modules.judge.application.dtos.verdict_dto import VerdictDTO
from src.modules.judge.container import JudgeContainer
from src.modules.judge.domain.dtos.judge_input import JudgeInput


def _debate_outcome_to_judge_input(symbol: str, debate_outcome: dict[str, Any]) -> JudgeInput:
    """
    从 debate_outcome dict 提取结论级字段，构造 JudgeInput。
    过滤 supporting_arguments、acknowledged_risks、probability/impact/mitigation 等细节。
    """
    bull_case = debate_outcome.get("bull_case") or {}
    bear_case = debate_outcome.get("bear_case") or {}
    risk_matrix = debate_outcome.get("risk_matrix") or []
    risk_factors = [
        item.get("risk", "") for item in risk_matrix if isinstance(item, dict) and item.get("risk")
    ]
    return JudgeInput(
        symbol=symbol,
        direction=str(debate_outcome.get("direction", "")),
        confidence=float(debate_outcome.get("confidence", 0.0)),
        bull_thesis=str(bull_case.get("core_thesis", "")),
        bear_thesis=str(bear_case.get("core_thesis", "")),
        risk_factors=risk_factors,
        key_disagreements=list(debate_outcome.get("key_disagreements") or []),
        conflict_resolution=str(debate_outcome.get("conflict_resolution", "")),
    )


class JudgeGatewayAdapter(IJudgeGateway):
    """
    通过 JudgeContainer 获取 JudgeService，将 debate_outcome 转为 JudgeInput，
    调用 run() 后返回 VerdictDTO 的 dict 形式。
    """

    def __init__(self, session_factory: Any) -> None:
        """
        与 DebateGatewayAdapter 一致，接受 session_factory 以保持接口统一。
        Judge 模块不依赖 DB，run_verdict 内不创建 AsyncSession。
        """
        self._session_factory = session_factory

    async def run_verdict(self, symbol: str, debate_outcome: dict[str, Any]) -> dict[str, Any]:
        """
        debate_outcome 转为 JudgeInput（仅结论级字段），调用 JudgeService.run，返回 .model_dump()。
        """
        judge_input = _debate_outcome_to_judge_input(symbol=symbol, debate_outcome=debate_outcome)
        container = JudgeContainer()
        service = container.judge_service()
        verdict: VerdictDTO = await service.run(judge_input)
        return verdict.model_dump()
