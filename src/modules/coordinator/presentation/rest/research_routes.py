"""
研究编排 REST 接口：POST /research。
"""
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.shared.domain.exceptions import BadRequestException
from src.shared.infrastructure.db.session import get_db_session
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.coordinator.application.research_orchestration_service import (
    ResearchOrchestrationService,
)
from src.modules.coordinator.container import CoordinatorContainer
from src.modules.coordinator.domain.exceptions import AllExpertsFailedError

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------- 请求/响应模型 ----------
class ResearchOrchestrationRequest(BaseModel):
    """研究编排请求体。"""

    symbol: str = Field(..., description="股票代码")
    experts: list[str] = Field(..., description="专家类型列表，如 ['technical_analyst', 'macro_intelligence']")
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


# ---------- 依赖注入 ----------
async def get_research_orchestration_service(
    db: AsyncSession = Depends(get_db_session),
) -> ResearchOrchestrationService:
    """通过 CoordinatorContainer 获取研究编排服务。"""
    return CoordinatorContainer(db).research_orchestration_service()


# ---------- 路由 ----------
@router.post(
    "/research",
    response_model=ResearchOrchestrationResponse,
    summary="研究编排",
    description="根据指定标的与专家列表，并行执行研究分析并汇总结果。",
)
async def post_research(
    body: ResearchOrchestrationRequest,
    service: ResearchOrchestrationService = Depends(get_research_orchestration_service),
) -> ResearchOrchestrationResponse:
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
        return ResearchOrchestrationResponse(
            symbol=result.symbol,
            overall_status=result.overall_status,
            expert_results=expert_results_dict,
            debate_outcome=result.debate_outcome,
            verdict=result.verdict,
        )
    except BadRequestException as e:
        raise HTTPException(status_code=400, detail=e.message)
    except AllExpertsFailedError as e:
        raise HTTPException(status_code=500, detail=e.message)
    except Exception as e:
        logger.exception("研究编排执行异常: %s", str(e))
        raise HTTPException(status_code=500, detail="研究编排执行失败，请稍后重试")
