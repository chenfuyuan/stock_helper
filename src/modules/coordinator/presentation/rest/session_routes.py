"""
历史研究会话查询 REST 接口：GET /research/sessions、/research/sessions/{id}、/llm-calls、/api-calls。
"""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.coordinator.application.dtos.session_dtos import (
    ExternalAPICallItemDTO,
    LLMCallItemDTO,
    SessionDetailDTO,
    SessionSummaryDTO,
)
from src.modules.coordinator.application.queries.session_detail_query import (
    SessionDetailQuery,
)
from src.modules.coordinator.application.queries.session_list_query import (
    SessionListQuery,
)
from src.modules.coordinator.infrastructure.persistence.research_session_repository import (
    PgResearchSessionRepository,
)
from src.modules.llm_platform.application.queries.llm_call_log_query_service import (
    LLMCallLogQueryService,
)
from src.modules.llm_platform.infrastructure.persistence.repositories.llm_call_log_repository import (
    PgLLMCallLogRepository,
)
from src.shared.application.queries.external_api_call_log_query_service import (
    ExternalAPICallLogQueryService,
)
from src.shared.infrastructure.db.session import get_db_session
from src.shared.infrastructure.persistence.external_api_call_log_repository import (
    PgExternalAPICallLogRepository,
)

router = APIRouter()


async def get_session_list_query(
    db: AsyncSession = Depends(get_db_session),
) -> SessionListQuery:
    """会话列表查询（依赖请求级 DB session）。"""
    repo = PgResearchSessionRepository(db)
    return SessionListQuery(repo)


async def get_session_detail_query(
    db: AsyncSession = Depends(get_db_session),
) -> SessionDetailQuery:
    """会话详情查询（依赖请求级 DB session）。"""
    repo = PgResearchSessionRepository(db)
    return SessionDetailQuery(repo)


@router.get(
    "/research/sessions",
    response_model=list[SessionSummaryDTO],
    summary="会话列表",
    description="分页查询研究会话列表，支持按 symbol、时间范围筛选。",
)
async def list_sessions(
    query: SessionListQuery = Depends(get_session_list_query),
    symbol: str | None = Query(None, description="股票代码筛选"),
    created_after: datetime | None = Query(
        None, description="创建时间起始（含）"
    ),
    created_before: datetime | None = Query(
        None, description="创建时间截止（含）"
    ),
    skip: int = Query(0, ge=0, description="跳过条数"),
    limit: int = Query(20, ge=1, le=100, description="每页条数"),
) -> list[SessionSummaryDTO]:
    """GET /research/sessions：会话列表，按 created_at 降序。"""
    return await query.execute(
        symbol=symbol,
        created_after=created_after,
        created_before=created_before,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/research/sessions/{session_id}",
    response_model=SessionDetailDTO,
    summary="会话详情",
    description="查询单次研究会话详情及全部节点执行记录。",
)
async def get_session_detail(
    session_id: UUID,
    query: SessionDetailQuery = Depends(get_session_detail_query),
) -> SessionDetailDTO:
    """GET /research/sessions/{session_id}：会话详情 + NodeExecution 列表。"""
    detail = await query.execute(session_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="会话不存在")
    return detail


@router.get(
    "/research/sessions/{session_id}/llm-calls",
    response_model=list[LLMCallItemDTO],
    summary="会话关联的 LLM 调用日志",
    description="返回该会话下所有 LLM 调用的审计日志（列表项，不含完整 prompt/completion）。",
)
async def list_session_llm_calls(
    session_id: UUID,
    db: AsyncSession = Depends(get_db_session),
) -> list[LLMCallItemDTO]:
    """GET /research/sessions/{session_id}/llm-calls：调用 llm_platform 查询服务。"""
    llm_repo = PgLLMCallLogRepository(db)
    llm_query = LLMCallLogQueryService(llm_repo)
    logs = await llm_query.get_by_session_id(session_id)
    return [
        LLMCallItemDTO(
            id=str(log.id),
            caller_module=log.caller_module,
            caller_agent=log.caller_agent,
            model_name=log.model_name,
            vendor=log.vendor,
            prompt_tokens=log.prompt_tokens,
            completion_tokens=log.completion_tokens,
            total_tokens=log.total_tokens,
            latency_ms=log.latency_ms,
            status=log.status,
            created_at=log.created_at,
        )
        for log in logs
    ]


@router.get(
    "/research/sessions/{session_id}/api-calls",
    response_model=list[ExternalAPICallItemDTO],
    summary="会话关联的外部 API 调用日志",
    description="返回该会话下所有外部 API 调用的审计日志（列表项）。",
)
async def list_session_api_calls(
    session_id: UUID,
    db: AsyncSession = Depends(get_db_session),
) -> list[ExternalAPICallItemDTO]:
    """GET /research/sessions/{session_id}/api-calls：调用 shared 查询服务。"""
    api_repo = PgExternalAPICallLogRepository(db)
    api_query = ExternalAPICallLogQueryService(api_repo)
    logs = await api_query.get_by_session_id(session_id)
    return [
        ExternalAPICallItemDTO(
            id=str(log.id),
            service_name=log.service_name,
            operation=log.operation,
            status_code=log.status_code,
            latency_ms=log.latency_ms,
            status=log.status,
            created_at=log.created_at,
        )
        for log in logs
    ]
