"""
Debate REST 路由：POST /api/v1/debate/run。
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from src.modules.debate.application.dtos.debate_outcome_dto import (
    DebateOutcomeDTO,
)
from src.modules.debate.application.services.debate_service import (
    DebateService,
)
from src.modules.debate.container import DebateContainer
from src.modules.debate.domain.dtos.debate_input import (
    DebateInput,
    ExpertSummary,
)
from src.modules.debate.domain.exceptions import LLMOutputParseError
from src.modules.debate.presentation.rest.debate_schemas import (
    DebateRunRequest,
    DebateRunResponse,
)
from src.shared.domain.exceptions import BadRequestException
from src.shared.dtos import BaseResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["debate"])


def _expert_results_to_debate_input(symbol: str, expert_results: dict[str, Any]) -> DebateInput:
    """
    将 REST 请求中的 expert_results（dict[str, dict]）转为 DebateInput。
    仅当 value 为 dict 且包含可映射字段时构造 ExpertSummary，否则跳过该专家。
    """
    summaries: dict[str, ExpertSummary] = {}
    for expert_key, data in expert_results.items():
        if not isinstance(data, dict):
            continue
        # 使用与 DebateGatewayAdapter 一致的归一化：若请求方已给 signal/confidence/reasoning/risk_warning 则直接用
        signal = (
            data.get("signal") or data.get("valuation_verdict") or data.get("macro_environment")
        )
        if isinstance(signal, dict):
            signal = str(signal.get("result", {}).get("catalyst_assessment", ""))
        if signal is None:
            signal = ""
        else:
            signal = str(signal)
        confidence = data.get("confidence") or data.get("confidence_score")
        if confidence is None and isinstance(data.get("result"), dict):
            confidence = data["result"].get("confidence_score")
        if confidence is None:
            confidence = 0.0
        else:
            confidence = float(confidence)
        reasoning = (
            data.get("reasoning")
            or data.get("summary_reasoning")
            or data.get("reasoning_summary")
            or data.get("macro_summary")
            or ""
        )
        if not reasoning and isinstance(data.get("result"), dict):
            reasoning = data["result"].get("catalyst_summary") or ""
        reasoning = str(reasoning) if reasoning is not None else ""
        risk = data.get("risk_warning") or data.get("risk_factors") or data.get("key_risks") or ""
        if not risk and isinstance(data.get("result"), dict):
            neg = data["result"].get("negative_catalysts")
            risk = ", ".join(neg) if isinstance(neg, list) else str(neg or "")
        if isinstance(risk, list):
            risk = ", ".join(str(x) for x in risk)
        risk = str(risk) if risk is not None else ""
        summaries[expert_key] = ExpertSummary(
            signal=signal,
            confidence=confidence,
            reasoning=reasoning,
            risk_warning=risk,
        )
    return DebateInput(symbol=symbol, expert_summaries=summaries)


async def get_debate_service() -> DebateService:
    """依赖注入：从 DebateContainer 获取 DebateService（无 DB 会话，使用默认构造）。"""
    return DebateContainer().debate_service()


@router.post(
    "/run",
    response_model=BaseResponse[DebateRunResponse],
    summary="执行辩论",
    description="根据标的与专家结果执行多空辩论，返回 DebateOutcome。",
)
async def post_debate_run(
    body: DebateRunRequest,
    service: DebateService = Depends(get_debate_service),
) -> BaseResponse[DebateRunResponse]:
    """POST /api/v1/debate/run：入参校验后调用 DebateService.run，异常映射为 HTTP 状态码。"""
    if not body.symbol or not str(body.symbol).strip():
        raise HTTPException(status_code=400, detail="symbol 为必填")
    if not body.expert_results:
        raise HTTPException(status_code=400, detail="expert_results 为必填且不能为空")
    try:
        debate_input = _expert_results_to_debate_input(
            symbol=body.symbol.strip(),
            expert_results=body.expert_results,
        )
        outcome: DebateOutcomeDTO = await service.run(debate_input)
        return BaseResponse(
            success=True,
            code="DEBATE_RUN_SUCCESS",
            message="辩论执行成功完成",
            data=DebateRunResponse(
                symbol=outcome.symbol,
                direction=outcome.direction,
                confidence=outcome.confidence,
                bull_case=outcome.bull_case.model_dump(),
                bear_case=outcome.bear_case.model_dump(),
                risk_matrix=[r.model_dump() for r in outcome.risk_matrix],
                key_disagreements=outcome.key_disagreements,
                conflict_resolution=outcome.conflict_resolution,
            )
        )
    except LLMOutputParseError as e:
        logger.warning("辩论 LLM 解析失败: %s", e.message)
        raise HTTPException(status_code=500, detail=e.message)
    except BadRequestException as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        logger.exception("辩论执行异常: %s", str(e))
        raise HTTPException(status_code=500, detail="辩论执行失败，请稍后重试")
