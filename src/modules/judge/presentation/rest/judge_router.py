"""
Judge REST 路由：POST /api/v1/judge/verdict。
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from src.modules.judge.application.dtos.verdict_dto import VerdictDTO
from src.modules.judge.application.services.judge_service import JudgeService
from src.modules.judge.container import JudgeContainer
from src.modules.judge.domain.dtos.judge_input import JudgeInput
from src.modules.judge.domain.exceptions import LLMOutputParseError
from src.modules.judge.presentation.rest.judge_schemas import (
    JudgeVerdictRequest,
    JudgeVerdictResponse,
)
from src.shared.domain.exceptions import AppException

logger = logging.getLogger(__name__)

router = APIRouter(tags=["judge"])


def _debate_outcome_to_judge_input(
    symbol: str, debate_outcome: dict[str, Any]
) -> JudgeInput:
    """将 REST 请求中的 debate_outcome dict 转为 JudgeInput。"""
    bull_case = debate_outcome.get("bull_case") or {}
    bear_case = debate_outcome.get("bear_case") or {}
    risk_matrix = debate_outcome.get("risk_matrix") or []
    risk_factors = [
        item.get("risk", "")
        for item in risk_matrix
        if isinstance(item, dict) and item.get("risk")
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


async def get_judge_service() -> JudgeService:
    """依赖注入：从 JudgeContainer 获取 JudgeService。"""
    return JudgeContainer().judge_service()


@router.post(
    "/verdict",
    response_model=JudgeVerdictResponse,
    summary="执行裁决",
    description="根据标的与辩论结果执行综合裁决，返回可执行操作指令。",
)
async def post_judge_verdict(
    body: JudgeVerdictRequest,
    service: JudgeService = Depends(get_judge_service),
) -> JudgeVerdictResponse:
    """POST /api/v1/judge/verdict：入参校验后调用 JudgeService.run，异常映射为 400/500。"""
    if not body.symbol or not str(body.symbol).strip():
        raise HTTPException(status_code=400, detail="symbol 为必填")
    if not body.debate_outcome or not isinstance(body.debate_outcome, dict):
        raise HTTPException(
            status_code=400, detail="debate_outcome 为必填且须为非空对象"
        )
    try:
        judge_input = _debate_outcome_to_judge_input(
            symbol=body.symbol.strip(),
            debate_outcome=body.debate_outcome,
        )
        verdict: VerdictDTO = await service.run(judge_input)
        return JudgeVerdictResponse(
            symbol=verdict.symbol,
            action=verdict.action,
            position_percent=verdict.position_percent,
            confidence=verdict.confidence,
            entry_strategy=verdict.entry_strategy,
            stop_loss=verdict.stop_loss,
            take_profit=verdict.take_profit,
            time_horizon=verdict.time_horizon,
            risk_warnings=verdict.risk_warnings,
            reasoning=verdict.reasoning,
        )
    except LLMOutputParseError as e:
        logger.warning("裁决 LLM 解析失败: %s", e.message)
        raise HTTPException(status_code=500, detail=e.message)
    except AppException as e:
        status = e.status_code if hasattr(e, "status_code") else 500
        raise HTTPException(status_code=status, detail=e.message)
    except Exception as e:
        logger.exception("裁决执行异常: %s", str(e))
        raise HTTPException(status_code=500, detail="裁决执行失败，请稍后重试")
