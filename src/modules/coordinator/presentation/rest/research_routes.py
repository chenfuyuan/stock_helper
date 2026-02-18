"""
研究编排 REST 接口：POST /research。
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.coordinator.application.research_orchestration_service import (
    ResearchOrchestrationService,
)
from src.modules.coordinator.container import CoordinatorContainer
from src.modules.coordinator.domain.dtos.research_dtos import (
    ResearchResult,
)
from src.modules.coordinator.domain.exceptions import (
    AllExpertsFailedError,
    SessionNotFoundError,
    SessionNotRetryableError,
)
from src.shared.domain.exceptions import BadRequestException
from src.shared.dtos import BaseResponse
from src.shared.infrastructure.db.session import get_db_session

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------- 请求/响应模型 ----------
class ResearchOrchestrationRequest(BaseModel):
    """研究编排请求体。"""

    symbol: str = Field(..., description="股票代码")
    experts: list[str] = Field(
        ...,
        description="专家类型列表，如 ['technical_analyst', 'macro_intelligence']",
    )
    options: dict[str, dict[str, Any]] = Field(
        default_factory=dict,
        description="各专家可选参数",
    )
    skip_debate: bool = Field(False, description="为 true 时跳过辩论阶段")


class ExpertResultApiItem(BaseModel):
    """单个专家结果的 API 响应项。"""

    status: str = Field(..., description="success 或 failed")
    data: dict[str, Any] | None = Field(None, description="成功时的分析结果")
    error: str | None = Field(None, description="失败时的错误信息")


class ResearchOrchestrationResponse(BaseModel):
    """研究编排响应体。"""

    symbol: str
    overall_status: str = Field(..., description="completed / partial / failed")
    expert_results: dict[str, ExpertResultApiItem] = Field(
        ...,
        description="按专家名分组的结果",
    )
    debate_outcome: dict[str, Any] | None = Field(
        None,
        description="辩论结果；skip_debate 或辩论失败时为 null",
    )
    verdict: dict[str, Any] | None = Field(
        None,
        description="裁决结果；skip_debate、辩论失败或裁决失败时为 null",
    )
    session_id: str = Field(
        "",
        description="研究会话 ID，用于历史查询与审计关联；未启用持久化时为空",
    )
    retry_count: int = Field(0, description="重试计数，首次执行为 0，每次重试递增 1")


# ---------- 依赖注入 ----------
async def get_research_orchestration_service(
    db: AsyncSession = Depends(get_db_session),
) -> ResearchOrchestrationService:
    """通过 CoordinatorContainer 获取研究编排服务。"""
    return CoordinatorContainer(db).research_orchestration_service()


# ---------- 路由 ----------
@router.post(
    "/research",
    response_model=BaseResponse[ResearchOrchestrationResponse],
    summary="研究编排",
    description="根据指定标的与专家列表，并行执行研究分析并汇总结果。",
)
async def post_research(
    body: ResearchOrchestrationRequest,
    service: ResearchOrchestrationService = Depends(get_research_orchestration_service),
) -> BaseResponse[ResearchOrchestrationResponse]:
    """
    执行研究编排：symbol + experts + options → 并行调用 Research 专家 → 汇总返回。
    """
    try:
        result = await service.execute(
            symbol=body.symbol,
            experts=body.experts,
            options=body.options or {},
            skip_debate=body.skip_debate,
        )
        # 转为 API 响应格式：expert_results 按专家名分组的 dict
        expert_results_dict: dict[str, ExpertResultApiItem] = {}
        for item in result.expert_results:
            key = item.expert_type.value
            if item.status == "success":
                expert_results_dict[key] = ExpertResultApiItem(
                    status="success",
                    data=item.data,
                    error=None,
                )
            else:
                expert_results_dict[key] = ExpertResultApiItem(
                    status="failed",
                    data=None,
                    error=item.error,
                )
        return BaseResponse(
            success=True,
            code="RESEARCH_ORCHESTRATION_SUCCESS",
            message="研究编排成功完成",
            data=ResearchOrchestrationResponse(
                symbol=result.symbol,
                overall_status=result.overall_status,
                expert_results=expert_results_dict,
                debate_outcome=result.debate_outcome,
                verdict=result.verdict,
                session_id=result.session_id,
                retry_count=result.retry_count,
            )
        )
    except BadRequestException as e:
        raise HTTPException(status_code=400, detail=e.message)
    except AllExpertsFailedError as e:
        raise HTTPException(status_code=500, detail=e.message)
    except Exception as e:
        logger.exception("研究编排执行异常: %s", str(e))
        raise HTTPException(status_code=500, detail="研究编排执行失败，请稍后重试")


# ---------- 重试请求模型 ----------
class RetryResearchRequest(BaseModel):
    """研究重试请求体。"""

    skip_debate: bool = Field(False, description="为 true 时跳过辩论阶段")


def _build_response(result: "ResearchResult") -> ResearchOrchestrationResponse:
    """将 ResearchResult 转为 API 响应格式。"""
    expert_results_dict: dict[str, ExpertResultApiItem] = {}
    for item in result.expert_results:
        key = item.expert_type.value
        if item.status == "success":
            expert_results_dict[key] = ExpertResultApiItem(
                status="success",
                data=item.data,
                error=None,
            )
        else:
            expert_results_dict[key] = ExpertResultApiItem(
                status="failed",
                data=None,
                error=item.error,
            )
    return ResearchOrchestrationResponse(
        symbol=result.symbol,
        overall_status=result.overall_status,
        expert_results=expert_results_dict,
        debate_outcome=result.debate_outcome,
        verdict=result.verdict,
        session_id=result.session_id,
        retry_count=result.retry_count,
    )


@router.post(
    "/research/{session_id}/retry",
    response_model=BaseResponse[ResearchOrchestrationResponse],
    summary="研究重试",
    description="对已有 session 中失败的专家发起重试，复用成功专家的结果，重新执行聚合/辩论/裁决。",
)
async def post_research_retry(
    session_id: str,
    body: RetryResearchRequest | None = None,
    service: ResearchOrchestrationService = Depends(get_research_orchestration_service),
) -> BaseResponse[ResearchOrchestrationResponse]:
    """
    重试研究编排：仅重新执行失败的专家，复用已成功的结果。
    """
    from uuid import UUID

    try:
        sid = UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="session_id 格式无效，必须为 UUID")

    skip_debate = body.skip_debate if body else False

    try:
        result = await service.retry(
            session_id=sid,
            skip_debate=skip_debate,
        )
        return BaseResponse(
            success=True,
            code="RESEARCH_RETRY_SUCCESS",
            message="研究重试成功完成",
            data=_build_response(result)
        )
    except SessionNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except SessionNotRetryableError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except AllExpertsFailedError as e:
        raise HTTPException(status_code=500, detail=e.message)
    except Exception as e:
        logger.exception("研究重试执行异常: %s", str(e))
        raise HTTPException(status_code=500, detail="研究重试执行失败，请稍后重试")
